# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QUndoCommand

from .animations import AnimatingTempRectItemABC
from .shift_page import Duration


class CommandRemovePage(QUndoCommand):
    """Remove or undo removing a page, not including cleanup moves of annotations."""

    def __init__(
        self, scene, src_id: int, page_image_idx: int, go_left: bool = False
    ) -> None:
        # scene type is plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.src_id = src_id
        self.page_image_idx = page_image_idx
        self.go_left = go_left
        self.setText("RotatePage")

    def redo(self):
        # TODO: is this the correct boundary?
        img = self.scene.underImage.images[self.page_image_idx]
        r = img.mapRectToScene(img.boundingRect())
        self.scene._set_visible_page_image(self.src_id, show=False)
        # temporary animation, removes itself when done
        if self.go_left:
            what = "disappear_left"
        else:
            what = "disappear_right"
        self.scene.addItem(TmpAnimDisappearingRectItem(r, what=what))

    def undo(self):
        self.scene._set_visible_page_image(self.src_id, show=True)
        # TODO: how to we figure out the index?
        img = self.scene.underImage.images[self.page_image_idx]
        r = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimDisappearingRectItem(r, what="restore"))


class TmpAnimDisappearingRectItem(AnimatingTempRectItemABC):
    def __init__(self, r: QRectF, *, what: str = "disappear_left") -> None:
        super().__init__()
        assert what in ("disappear_left", "disappear_right", "restore")
        self.what = what
        if what == "disappear_left":
            r.moveLeft(r.left() - r.width())
        self.setRect(r)

        self.anim.setDuration(Duration)
        if what == "restore":
            self.anim.setStartValue(1)
            self.anim.setEndValue(0)
        else:
            self.anim.setStartValue(0)
            self.anim.setEndValue(1)

        self.start()

    def interp(self, t: float) -> None:
        """Draw a rectangle part way between r and zooming out to nothing.

        Args:
            t: a value in [0, 1].

        Returns:
            None
        """
        if self.what == "restore":
            self.setTransformOriginPoint(self.boundingRect().center())
        elif self.what == "disappear_left":
            self.setTransformOriginPoint(
                (self.boundingRect().topRight() + self.boundingRect().bottomRight())
                / 2.0
            )
        elif self.what == "disappear_right":
            self.setTransformOriginPoint(
                (self.boundingRect().topLeft() + self.boundingRect().bottomLeft()) / 2.0
            )
        else:
            raise RuntimeError("Tertium non datur")
        self.setScale(1 - t)
