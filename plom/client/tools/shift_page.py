# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QUndoCommand

from .animations import AnimatingTempRectItemABC, AnimationDuration


# this is a large-scale animation: slow it down a bit
Duration = 3 * AnimationDuration // 2


class CommandShiftPage(QUndoCommand):
    """Do or undo a translation of a page, not including cleanup moves of annotations."""

    def __init__(self, scene, old_idx: int, new_idx: int) -> None:
        # scene type is plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.old_idx = old_idx
        self.new_idx = new_idx
        self.setText("RotatePage")

    def redo(self):
        # TODO: is this the correct boundary?
        img = self.scene.underImage.images[self.old_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._shift_page_image_only(self.old_idx, self.new_idx)
        img = self.scene.underImage.images[self.new_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimRectItem(r1, r2))

    def undo(self):
        img = self.scene.underImage.images[self.new_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._shift_page_image_only(self.new_idx, self.old_idx)
        img = self.scene.underImage.images[self.old_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimRectItem(r1, r2))


class TmpAnimRectItem(AnimatingTempRectItemABC):
    def __init__(self, r1: QRectF, r2: QRectF) -> None:
        super().__init__()
        self.r1 = r1
        self.r2 = r2
        self.anim.setDuration(Duration)
        self.start()

    def interp(self, t: float) -> None:
        """Draw a rectangle part way between r1 and r2, with a zoom out effect.

        Args:
            t: a value in [0, 1].

        Returns:
            None
        """
        r1 = self.r1
        r2 = self.r2
        # r = t*r1 + (1-t)*r2
        r = QRectF(
            (1 - t) * r1.left() + t * r2.left(),
            (1 - t) * r1.top() + t * r2.top(),
            (1 - t) * r1.width() + t * r2.width(),
            (1 - t) * r1.height() + t * r2.height(),
        )
        self.setRect(r)
        # zoom out to two-thirds during the animation
        s = (2 + (2 * t - 1) ** 2) / 3.0
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setScale(s)
