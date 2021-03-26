# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QUndoCommand

from plom.client.tools import DeltaItem, GroupDeltaTextItem


class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a rubric-item - need to refresh score in parent-scene
    # and be careful that is done once the item is actually deleted.
    def __init__(self, scene, deleteItem):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.setText("Delete")

    def redo(self):
        # check to see if mid-delete
        if self.deleteItem.animateFlag:
            return  # this avoids user deleting same object mid-delete animation.

        # nicely animate the deletion - since deleting, this is like an "undo"
        self.deleteItem.animateFlag = True
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_undo()
            QTimer.singleShot(200, lambda: self.scene.removeItem(self.deleteItem))
            # after everything removed - refresh the state and score
            if isinstance(self.deleteItem, GroupDeltaTextItem):
                QTimer.singleShot(250, self.scene.refreshStateAndScore)
        else:
            self.scene.removeItem(self.deleteItem)
            # after everything removed - refresh the state and score
            if isinstance(self.deleteItem, GroupDeltaTextItem):
                self.scene.refreshStateAndScore()

    def undo(self):
        # nicely animate the undo of deletion
        self.deleteItem.animateFlag = False
        self.scene.addItem(self.deleteItem)
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_redo()
        # If the object is a GroupTextDeltaItem then refresh the state and score
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            self.scene.refreshStateAndScore()
