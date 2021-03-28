# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QTimer, pyqtProperty, QRectF, QPropertyAnimation
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsRectItem,
    QGraphicsItem,
)


# from plom.client.tools import DeltaItem, GroupDeltaTextItem


class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a delta-item which changes the current mark
    def __init__(self, scene, deleteItem):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.setText("Delete")

    def redo(self):
        # check to see if mid-delete
        if self.deleteItem.animateFlag:
            return  # this avoids user deleting same object mid-delete animation.

        # If the object is a DeltaItem then change mark
        if isinstance(self.deleteItem, DeltaItem):
            # Mark decreases by delta - since deleting, this is like an "undo"
            self.scene.changeTheMark(self.deleteItem.delta, undo=True)
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=True)
        # nicely animate the deletion - since deleting, this is like an "undo"
        self.deleteItem.animateFlag = True
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_undo()
            QTimer.singleShot(200, lambda: self.scene.removeItem(self.deleteItem))
        else:
            self.scene.removeItem(self.deleteItem)

    def undo(self):
        # If the object is a DeltaItem then change mark.
        if isinstance(self.deleteItem, DeltaItem):
            # Mark increases by delta  - since deleting, this is like an "redo"
            self.scene.changeTheMark(self.deleteItem.delta, undo=False)
        # If the object is a GroupTextDeltaItem then change mark
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            # Mark decreases by delta -  - since deleting, this is like an "redo"
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=False)
        # nicely animate the undo of deletion
        self.deleteItem.animateFlag = False
        self.scene.addItem(self.deleteItem)
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_redo()


## For animation of undo / redo / delete


class DeleteObject(QGraphicsObject):
    # As per the ArrowItemObject, except animate the opacity of the box.
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
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.initialRect = rect
        self.padding = 0
        self.setRect(self.initialRect)
        self.restyle(style)

    def restyle(self, style):
        self.setPen(QPen(QColor(255, 255, 0, 32), 1, style=Qt.DashLine))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
