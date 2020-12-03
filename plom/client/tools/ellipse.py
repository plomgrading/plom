# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsEllipseItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandEllipse(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, rect):
        super(CommandEllipse, self).__init__()
        self.scene = scene
        self.rect = rect
        self.ellipseItem = EllipseItemObject(self.rect)
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
        self.ellipseItem.flash_redo()
        self.scene.addItem(self.ellipseItem.ei)

    def undo(self):
        self.ellipseItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.ellipseItem.ei))


class EllipseItemObject(QGraphicsObject):
    # As per the ArrowItemObject - animate thickness of boundary
    def __init__(self, rect):
        super(EllipseItemObject, self).__init__()
        self.ei = EllipseItem(rect, self)
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
        return self.ei.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ei.setPen(QPen(Qt.red, value))


class EllipseItem(QGraphicsEllipseItem):
    # Very similar to the arrowitem
    def __init__(self, rect, parent=None):
        super(EllipseItem, self).__init__()
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
        return QGraphicsEllipseItem.itemChange(self, change, value)

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
        super(EllipseItem, self).paint(painter, option, widget)
