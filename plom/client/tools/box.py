# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsRectItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandBox(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, rect):
        super(CommandBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.boxItem = BoxItemObject(self.rect)
        self.setText("Box")

    def redo(self):
        self.boxItem.flash_redo()
        self.scene.addItem(self.boxItem.bi)

    def undo(self):
        self.boxItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.boxItem.bi))


class BoxItemObject(QGraphicsObject):
    # As per the ArrowItemObject, except animate the opacity of the box.
    def __init__(self, rect):
        super(BoxItemObject, self).__init__()
        self.bi = BoxItem(rect, self)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        # translucent -> opaque -> clear.
        self.anim.setDuration(200)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # translucent -> opaque -> translucent.
        self.anim.setDuration(200)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 64)
        self.anim.setEndValue(16)
        self.anim.start()

    @pyqtProperty(int)
    def opacity(self):
        return self.bi.brush().color().alpha()

    @opacity.setter
    def opacity(self, value):
        self.bi.setBrush(QBrush(QColor(255, 255, 0, value)))


class BoxItem(QGraphicsRectItem):
    # Very similar to the arrowitem but simpler to draw the box.
    def __init__(self, rect, parent=None):
        super(BoxItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.rect = rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsRectItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Box",
            self.rect.left() + self.x(),
            self.rect.top() + self.y(),
            self.rect.width(),
            self.rect.height(),
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            # paint a bounding rectangle out-of-bounds warning
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(BoxItem, self).paint(painter, option, widget)
