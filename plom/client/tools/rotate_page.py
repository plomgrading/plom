# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtGui import QUndoCommand


class CommandRotatePage(QUndoCommand):
    """Do or undo a rotation of a page, not including cleanup moves of annotations."""

    def __init__(self, scene, page_image_idx: int, degrees: int) -> None:
        # scene type is plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.page_image_idx = page_image_idx
        self.degrees = degrees
        self.setText("RotatePage")

    def redo(self):
        self.scene._rotate_page_image(
            self.page_image_idx, self.degrees, move_objects=False
        )

    def undo(self):
        self.scene._rotate_page_image(
            self.page_image_idx, -self.degrees, move_objects=False
        )
