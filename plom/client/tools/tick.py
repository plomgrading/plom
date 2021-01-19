# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QPointF, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandTick(QUndoCommand):
    def __init__(self, scene, pt):
        super().__init__()
        self.scene = scene
        self.obj = TickItemObject(pt, scene.style)
        self.setText("Tick")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandTick from a serialized form."""
        assert X[0] == "Tick"
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


class TickItemObject(QGraphicsObject):
    def __init__(self, pt, style):
        super().__init__()
        self.item = TickItem(pt, style=style, parent=self)
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


class TickItem(QGraphicsPathItem):
    def __init__(self, pt, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.pt = pt
        self.path = QPainterPath()
        # Draw the checkmark with barycentre under mouseclick.
        self.path.moveTo(pt.x() - 10, pt.y() - 10)
        self.path.lineTo(pt.x(), pt.y())
        self.path.lineTo(pt.x() + 20, pt.y() - 20)
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
        return ["Tick", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
