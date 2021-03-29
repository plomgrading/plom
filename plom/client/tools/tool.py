# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsRectItem,
    QUndoCommand,
)


class CommandTool(QUndoCommand):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        # self.obj = QGraphicsRectItem()
        # self.do = DeleteObject(self.obj.boundingRect(), scene.style)

    def redo(self):
        self.scene.addItem(self.obj)
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_redo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))

    def undo(self):
        self.scene.removeItem(self.obj)
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_redo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))


## For animation of undo / redo / delete


class DeleteObject(QGraphicsObject):
    def __init__(self, rect, style):
        super().__init__()
        self.item = DeleteItem(rect, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        """Undo animation: thin -> thick -> none."""
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(-4)
        self.anim.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin."""
        self.anim.setStartValue(-4)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.item.padding

    @thickness.setter
    def thickness(self, value):
        self.item.padding = value
        self.item.setRect(self.item.initialRect.adjusted(-value, -value, value, value))


class DeleteItem(QGraphicsRectItem):
    def __init__(self, rect, style, parent=None):
        super().__init__()
        self.saveable = False
        self.initialRect = rect
        self.padding = 0
        self.setRect(self.initialRect)
        self.restyle(style)

    def restyle(self, style):
        self.setPen(QPen(QColor(255, 128, 0, 128), 2, style=Qt.DashLine))
        self.setBrush(QBrush(QColor(255, 128, 0, 32)))
