# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsEllipseItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandEllipse(QUndoCommand):
    def __init__(self, scene, rect):
        super().__init__()
        self.scene = scene
        self.obj = EllipseItemObject(rect, scene.style)
        self.setText("Ellipse")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandEllipse from a serialized form."""
        assert X[0] == "Ellipse"
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


class EllipseItemObject(QGraphicsObject):
    # As per the ArrowItemObject - animate thickness of boundary
    def __init__(self, rect, style):
        super().__init__()
        self.item = EllipseItem(rect, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.item.pen().width()

    @thickness.setter
    def thickness(self, value):
        pen = self.item.pen()
        pen.setWidthF(value)
        self.item.setPen(pen)


class EllipseItem(QGraphicsEllipseItem):
    def __init__(self, rect, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.rect = rect
        self.setRect(self.rect)
        self.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        return [
            "Ellipse",
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
