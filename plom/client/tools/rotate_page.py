# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QUndoCommand

from .animations import AnimatingTempRectItemABC
from .shift_page import Duration


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
        # TODO: is this the correct boundary?
        img = self.scene.underImage.images[self.page_image_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._rotate_page_image_only(self.page_image_idx, self.degrees)
        img = self.scene.underImage.images[self.page_image_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimRotatingRectItem(self.degrees, r1, r2))

    def undo(self):
        img = self.scene.underImage.images[self.page_image_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._rotate_page_image_only(self.page_image_idx, -self.degrees)
        img = self.scene.underImage.images[self.page_image_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimRotatingRectItem(-self.degrees, r1, r2))


class TmpAnimRotatingRectItem(AnimatingTempRectItemABC):
    def __init__(self, degrees: int, r1: QRectF, r2: QRectF) -> None:
        super().__init__()
        self.anim.setDuration(Duration)
        self.r1 = r1
        self.r2 = r2
        self.degrees = degrees

        self.start()

    def interp(self, t: float) -> None:
        """Draw a rectangle part way between r1 and r2, with a zoom out and rotate effect.

        Args:
            t: a value in [0, 1].

        Returns:
            None

        The rectangle starts (at t=0) from r1 and transforms into r2.  Currently we
        don't strictly speaking interpolate and instead use a square centered on a
        path from r1 to r2.
        """
        r1 = self.r1
        r2 = self.r2
        p = (1 - t) * r1.center() + t * r2.center()
        angle = (1 - t) * self.degrees
        # TODO: r = t*r1 + (1-t)*r2
        # self.setRect(r)
        w = min(r1.width(), r1.height(), r2.width(), r2.height()) / 4
        # 2*w size decreasing to w, then back up to 2*w
        w = w + w * (2 * t - 1) ** 2
        self.setRect(p.x() - w, p.y() - w, 2 * w, 2 * w)
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setRotation(angle)
