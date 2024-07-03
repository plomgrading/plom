# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020, 2022-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2024 Aden Chan

from PyQt6.QtGui import QPainterPath

from plom.client.tools import CommandTool


class CommandDelete(CommandTool):
    # Deletes the graphicsitem. Have to be careful when it is
    # a rubric-item - need to refresh score in parent-scene
    # and be careful that is done once the item is actually deleted.
    def __init__(self, scene, deleteItem):
        super().__init__(scene)
        self.deleteItem = deleteItem
        self.setText("Delete")

    def get_undo_redo_animation_shape(self) -> QPainterPath:
        # TODO: this is not quite right b/c that particular item might have custom
        # animation stuff.  But that is (currently) associated with the Command, not
        # the item itself.
        # TODO: maybe it would be better if each item can answer an appropriate shape
        return self.deleteItem.shape()

    def redo(self):
        self.scene.removeItem(self.deleteItem)
        # not a typo: redoing a delete is an removal action; use the undo animation
        self.undo_animation()

    def undo(self):
        # not a typo: undoing a delete is placing an obj; use the redo animation
        self.redo_animation()
        self.scene.addItem(self.deleteItem)
