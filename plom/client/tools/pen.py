# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem, log


class CommandPen(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandPen, self).__init__()
        self.scene = scene
        self.path = path
        self.penItem = PenItemObject(self.path)
        self.setText("Pen")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandPen from a serialized form.

        Raises:
            ValueError: malformed or otherwise incorrect data
            AssertionError: there is a bug somewhere.

        TODO: all these Pen-like annotations should subclass pen
        and inherit this function.
        """
        assert X[0] == "Pen"
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
        self.penItem.flash_redo()
        self.scene.addItem(self.penItem.pi)

    def undo(self):
        self.penItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.penItem.pi))


class PenItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, path):
        super(PenItemObject, self).__init__()
        self.pi = PenItem(path, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.pi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.pi.setPen(QPen(Qt.red, value))


class PenItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path, parent=None):
        super(PenItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
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
                    log.error("Problem pickling penitem path {}".format(self.path))
        return ["Pen", pth]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(PenItem, self).paint(painter, option, widget)
