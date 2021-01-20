# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QPointF, QTimer, QPropertyAnimation
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem
from plom.client.tools.tick import TickItemObject


class CommandCross(QUndoCommand):
    def __init__(self, scene, pt):
        super().__init__()
        self.scene = scene
        self.obj = CrossItemObject(pt, scene.style)
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
        self.obj.flash_redo()
        self.scene.addItem(self.obj.item)

    def undo(self):
        self.obj.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.obj.item))


class CrossItemObject(TickItemObject):
    def __init__(self, pt, style):
        super(TickItemObject, self).__init__()
        self.item = CrossItem(pt, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")


class CrossItem(QGraphicsPathItem):
    def __init__(self, pt, style, parent=None):
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
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = 3 * style["pen_width"] / 2
        self.setPen(QPen(style["annot_color"], self.normal_thick))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        return ["Cross", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
