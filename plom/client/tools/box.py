# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, QRectF
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsRectItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandBox(QUndoCommand):
    def __init__(self, scene, rect):
        super().__init__()
        self.scene = scene
        self.obj = BoxItemObject(rect, scene.style)
        self.setText("Box")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandBox from a serialized form."""
        assert X[0] == "Box"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QRectF(X[0], X[1], X[2], X[3]))

    def redo(self):
        self.obj.flash_redo()
        self.scene.addItem(self.obj.item)

    def undo(self):
        self.obj.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.obj.item))


class BoxItemObject(QGraphicsObject):
    # As per the ArrowItemObject, except animate the opacity of the box.
    def __init__(self, rect, style):
        super().__init__()
        self.item = BoxItem(rect, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        """Undo animation: thin -> thick -> none."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 4 * t)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 3 * t)
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


class BoxItem(QGraphicsRectItem):
    def __init__(self, rect, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.rect = rect
        self.setRect(self.rect)
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.setBrush(QBrush(style["box_tint"]))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        return [
            "Box",
            self.rect.left() + self.x(),
            self.rect.top() + self.y(),
            self.rect.width(),
            self.rect.height(),
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
