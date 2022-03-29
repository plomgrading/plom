# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020, 2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QUndoCommand

from plom.client.tools.rubric import GroupDeltaTextItem
from plom.client.tools import DeleteObject


class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a rubric-item - need to refresh score in parent-scene
    # and be careful that is done once the item is actually deleted.
    def __init__(self, scene, deleteItem):
        super().__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.setText("Delete")
        # the delete animation object
        self.do = DeleteObject(self.deleteItem.shape())

    def redo(self):
        # remove the object
        self.scene.removeItem(self.deleteItem)
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            self.scene.refreshStateAndScore()
        # flash an animated box around the deleted object
        self.scene.addItem(self.do.item)
        self.do.flash_undo()  # note - is undo animation since object being removed
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))

    def undo(self):
        # flash an animated box around the un-deleted object
        self.scene.addItem(self.do.item)
        self.do.flash_redo()  # is redo animation since object being brought back
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))
        # put the object back
        self.scene.addItem(self.deleteItem)
        # If the object is a GroupTextDeltaItem then refresh the state and score
        if isinstance(self.deleteItem, GroupDeltaTextItem):
            self.scene.refreshStateAndScore()


class CommandCrop(QUndoCommand):
    def __init__(self, scene, crop_rect, current_rect):
        super().__init__()
        self.scene = scene

        self.crop_rect = crop_rect
        self.prev_crop = current_rect
        self.setText("Crop")

    def redo(self):
        self.scene.croppit(self.crop_rect)

    def undo(self):
        self.scene.croppit(self.prev_crop)

