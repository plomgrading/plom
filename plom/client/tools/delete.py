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

from plom.client.tools.rubric import GroupDeltaTextItem


class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a delta-item which changes the current mark
    def __init__(self, scene, deleteItem):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.setText("Delete")

    def redo(self):
        # If the object is a DeltaItem then change mark
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=True)
        self.scene.removeItem(self.deleteItem)

    def undo(self):
        # If the object is a GroupTextDeltaItem then change mark
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            # Mark decreases by delta -  - since deleting, this is like an "redo"
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=False)
        self.scene.addItem(self.deleteItem)
