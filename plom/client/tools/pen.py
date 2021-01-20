# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem, log


class CommandPen(QUndoCommand):
    def __init__(self, scene, path):
        super().__init__()
        self.scene = scene
        self.penobj = PenItemObject(path, scene.style)
        self.setText("Pen")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Reconstruct from a serialized form.

        Raises:
            ValueError: malformed or otherwise incorrect data
            AssertionError: there is a bug somewhere.

        Other Pen-like annotations subclasses inherit this function.
        """
        assert cls.__name__.endswith(X[0]), 'Type "{}" mismatch: "{}"'.format(X[0], cls)
        X = X[1:]
        if len(X) != 1:
            raise ValueError("wrong length of pickle data")
        # Format is X = [['m',x,y], ['l',x,y], ['l',x,y], ...]
        X = X[0]
        pth = QPainterPath()
        # unpack ['m', x, y] or ValueError
        cmd, x, y = X[0]
        if cmd != "m":
            raise ValueError("malformed start of Pen-like annotation")
        pth.moveTo(QPointF(x, y))
        for pt in X[1:]:
            # unpack ['l', x, y] or ValueError
            cmd, x, y = pt
            if cmd != "l":
                raise ValueError("malformed Pen-like annotation in interior")
            pth.lineTo(QPointF(x, y))
        return cls(scene, pth)

    def redo(self):
        """Item knows how to highlight on undo and redo."""
        self.penobj.flash_redo()
        self.scene.addItem(self.penobj.item)

    def undo(self):
        """Undo animation takes 0.5s, so trigger removal after 0.5s."""
        self.penobj.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.penobj.item))


class PenItemObject(QGraphicsObject):
    def __init__(self, path, style):
        super().__init__()
        self.item = PenItem(path, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        """Undo animation: thin -> thick -> none."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 3 * t)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 2 * t)
        self.anim.setEndValue(t)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.item.pen().width()

    @thickness.setter
    def thickness(self, value):
        pen = self.item.pen()
        pen.setWidthF(value)
        self.item.setPen(pen)


class PenItem(QGraphicsPathItem):
    def __init__(self, path, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.path = path
        self.setPath(self.path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(QPen(style["annot_color"], style["pen_width"]))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        name = self.__class__.__name__.replace("Item", "")  # i.e., "Pen",
        pth = []
        for k in range(self.path.elementCount()):
            # e should be either a moveTo or a lineTo
            e = self.path.elementAt(k)
            if e.isMoveTo():
                pth.append(["m", e.x + self.x(), e.y + self.y()])
            else:
                if e.isLineTo():
                    pth.append(["l", e.x + self.x(), e.y + self.y()])
                else:
                    log.error("Problem pickling Pen-like path {}".format(self.path))
        return [name, pth]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
