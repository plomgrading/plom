# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QGraphicsObject,
    QGraphicsPathItem,
    QUndoCommand,
)


class CommandTool(QUndoCommand):
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        # obj and do need to be done by each tool
        # self.obj = QGraphicsItem()
        # self.do = DeleteObject(self.obj.shape())

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
        self.do.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))


# For animation of undo / redo / delete


class DeleteObject(QGraphicsObject):
    def __init__(self, shape, fill=False):
        super().__init__()
        self.item = DeleteItem(shape, fill=fill)
        self.anim_thick = QPropertyAnimation(self, b"thickness")
        self.anim_thick.setDuration(200)

    def flash_undo(self):
        """Undo animation: thin -> thick -> none."""
        self.anim_thick.setStartValue(2)
        self.anim_thick.setKeyValueAt(0.5, 8)
        self.anim_thick.setEndValue(0)

        self.anim_thick.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin."""
        self.anim_thick.setStartValue(0)
        self.anim_thick.setKeyValueAt(0.5, 8)
        self.anim_thick.setEndValue(2)

        self.anim_thick.start()

    @pyqtProperty(float)
    def thickness(self):
        return self.item.thickness

    @thickness.setter
    def thickness(self, value):
        self.item.restyle(value)


class DeleteItem(QGraphicsPathItem):
    def __init__(self, shape, fill=False):
        super().__init__()
        self.saveable = False
        self.initialShape = shape
        self.thickness = 2
        self.setPath(self.initialShape)
        self.restyle(self.thickness)
        if fill:
            self.setBrush(QBrush(QColor(8, 232, 222, 16)))

    def restyle(self, value):
        self.thickness = value
        self.setPen(QPen(QColor(8, 232, 222, 128), value))
