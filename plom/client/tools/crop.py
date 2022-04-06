# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer

from PyQt5.QtWidgets import QUndoCommand


class CommandCrop(QUndoCommand):
    def __init__(self, scene, crop_rect, current_rect):
        super().__init__()
        self.scene = scene

        self.crop_rect = crop_rect  # is absolute - not proportions
        self.prev_crop = current_rect  # is absolute - not proportions
        self.setText("Crop")

    def redo(self):
        self.scene._crop_to_focus(self.crop_rect)

    def undo(self):
        self.scene._crop_to_focus(self.prev_crop)
