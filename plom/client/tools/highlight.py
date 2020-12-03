# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem, log


class CommandHighlight(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandHighlight, self).__init__()
        self.scene = scene
        self.path = path
        self.highLightItem = HighLightItemObject(self.path)
        self.setText("Highlight")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandHighlight from a serialized form.

        Raises:
            ValueError: malformed or otherwise incorrect data
            AssertionError: there is a bug somewhere.

        TODO: all these Pen-like annotations should subclass pen
        and inherit this function.
        """
        assert X[0] == "Highlight"
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
        self.highLightItem.flash_redo()
        self.scene.addItem(self.highLightItem.hli)

    def undo(self):
        self.highLightItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.highLightItem.hli))


class HighLightItemObject(QGraphicsObject):
    # As per the ArrowItemObject except animate the opacity of
    # the highlighter path
    def __init__(self, path):
        super(HighLightItemObject, self).__init__()
        self.hli = HighLightItem(path, self)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 96)
        self.anim.setEndValue(64)
        self.anim.start()

    @pyqtProperty(int)
    def opacity(self):
        return self.hli.pen().color().alpha()

    @opacity.setter
    def opacity(self, value):
        self.hli.setPen(QPen(QColor(255, 255, 0, value), 50))


class HighLightItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path, parent=None):
        super(HighLightItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(QColor(255, 255, 0, 64), 50))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # self.dump()

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
                    log.error(
                        "Problem pickling highlightitem path {}".format(self.path)
                    )
        return ["Highlight", pth]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(HighLightItem, self).paint(painter, option, widget)
