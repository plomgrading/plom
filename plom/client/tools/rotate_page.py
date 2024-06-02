# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtGui import QUndoCommand


class CommandRotatePage(QUndoCommand):
    def __init__(self, scene, page_image_idx: int, degrees: int) -> None:
        # scene: plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.page_image_idx = page_image_idx
        self.degrees = degrees
        self.setText("RotatePage")

    def redo(self):
        print("redoing page rotate")
        self.scene._rotate_page_image(self.page_image_idx, self.degrees)

    def undo(self):
        print("undoing page rotate")
        self.scene._rotate_page_image(self.page_image_idx, -self.degrees)
