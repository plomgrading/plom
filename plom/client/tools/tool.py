# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021, 2023-2024 Colin B. Macdonald

from PyQt6.QtCore import QTimer, QPropertyAnimation
from PyQt6.QtCore import pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QPen, QUndoCommand
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsPathItem

from plom.client.tools import AnimationDuration as Duration


class CommandTool(QUndoCommand):
    """Handles the do/undo of edits to the PageScene.

    Subclasses will implement the ``obj`` which is the actual object to be
    drawn, and the ``do`` (the "DeleteObject") which is used for transcient
    animations.  Commands are free to subclass ``QUndoCommand`` themselves
    rather than subclassing this ``CommandTool``.

    The :py:method:`redo` method handles both the initial drawing and any
    subsequent draw operations to due to undo/redo cycles.

    Thus far, the ``redo`` method should not create subcommand objects:
    in my experience, hard to debug and segfault behaviour comes from
    trying.  Instead, macros are instead created in PageScene.  This
    could be revisited in the future.
    """

    def __init__(self, scene) -> None:
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
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(self.do.item))

    def undo(self):
        self.scene.removeItem(self.obj)
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_undo()
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(self.do.item))


# For animation of undo / redo / delete


class DeleteObject(QGraphicsObject):
    def __init__(self, shape, fill: bool = False) -> None:
        super().__init__()
        self.item = DeleteItem(shape, fill=fill)
        self.anim_thick = QPropertyAnimation(self, b"thickness")
        self.anim_thick.setDuration(Duration)

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
    def thickness(self) -> float:
        return self.item.thickness

    @thickness.setter
    def thickness(self, value: float) -> None:
        self.item.restyle(value)


class DeleteItem(QGraphicsPathItem):
    def __init__(self, shape, fill: bool = False) -> None:
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
