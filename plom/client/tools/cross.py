# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandCross(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, pt):
        super(CommandCross, self).__init__()
        self.scene = scene
        self.pt = pt
        self.crossItem = CrossItemObject(self.pt)
        self.setText("Cross")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandCross from a serialized form."""
        assert X[0] == "Cross"
        X = X[1:]
        if len(X) != 2:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]))

    def redo(self):
        self.crossItem.flash_redo()
        self.scene.addItem(self.crossItem.ci)

    def undo(self):
        self.crossItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.crossItem.ci))


class CrossItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(CrossItemObject, self).__init__()
        self.ci = CrossItem(pt, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.ci.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ci.setPen(QPen(Qt.red, value))


class CrossItem(QGraphicsPathItem):
    # Very similar to the arrowitem.
    def __init__(self, pt, parent=None):
        super(CrossItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.pt = pt
        self.path = QPainterPath()
        # Draw a cross whose vertex is at pt (under mouse click)
        self.path.moveTo(pt.x() - 12, pt.y() - 12)
        self.path.lineTo(pt.x() + 12, pt.y() + 12)
        self.path.moveTo(pt.x() - 12, pt.y() + 12)
        self.path.lineTo(pt.x() + 12, pt.y() - 12)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # self.dump()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return ["Cross", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
            # paint the normal item with the default 'paint' method
        super(CrossItem, self).paint(painter, option, widget)
