# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF, QObject
from PyQt6.QtCore import QPropertyAnimation, QAbstractAnimation
from PyQt6.QtCore import pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtGui import QBrush, QPen, QUndoCommand
from PyQt6.QtWidgets import QGraphicsRectItem

from plom.client.tools import log
from plom.client.tools import (
    AnimationPenColour,
    AnimationPenThickness,
    AnimationFillColour,
)
from .shift_page import Duration


class CommandRemovePage(QUndoCommand):
    """Remove or undo removing a page, not including cleanup moves of annotations."""

    def __init__(
        self, scene, src_idx: int, page_image_idx: int, go_left: bool = False
    ) -> None:
        # scene type is plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.src_idx = src_idx
        self.page_image_idx = page_image_idx
        self.go_left = go_left
        self.setText("RotatePage")

    def redo(self):
        # TODO: is this the correct boundary?
        img = self.scene.underImage.images[self.page_image_idx]
        r = img.mapRectToScene(img.boundingRect())
        self.scene._set_visible_page_image(self.src_idx, show=False)
        # temporary animation, removes itself when done
        if self.go_left:
            what = "disappear_left"
        else:
            what = "disappear_right"
        self.scene.addItem(TmpAnimDisappearingRectItem(self.scene, r, what=what))

    def undo(self):
        self.scene._set_visible_page_image(self.src_idx, show=True)
        # TODO: how to we figure out the index?
        img = self.scene.underImage.images[self.page_image_idx]
        r = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimDisappearingRectItem(self.scene, r, what="restore"))


# see comments about this class in `shift_page.py`
class TmpAnimDisappearingRectItem(QGraphicsRectItem):
    def __init__(self, scene, r: QRectF, *, what: str = "disappear_left") -> None:
        super().__init__()
        self._scene = scene
        self.saveable = False
        assert what in ("disappear_left", "disappear_right", "restore")
        self.what = what
        if what == "disappear_left":
            r.moveLeft(r.left() - r.width())
        self.r = r
        self.setRect(r)
        self.setPen(QPen(AnimationPenColour, AnimationPenThickness))
        self.setBrush(QBrush(AnimationFillColour))

        # Crashes when calling our methods (probably b/c QGraphicsItem
        # is not QObject).  Instead we use a helper class.
        self._ctrlr = _AnimatorCtrlr(self)
        self.anim = QPropertyAnimation(self._ctrlr, b"foo")

        self.anim.setDuration(Duration)
        if what == "restore":
            self.anim.setStartValue(1)
            self.anim.setEndValue(0)
        else:
            self.anim.setStartValue(0)
            self.anim.setEndValue(1)
        # When the animation finishes, it will destroy itself, whence
        # we'll get a callback to remove ourself from the scene
        self.anim.destroyed.connect(self.remove_from_scene)
        self.anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def remove_from_scene(self) -> None:
        log.debug(f"TmpAnimItem: removing {self} from scene")
        # TODO: can we be sure that scene survives until the end of the animation?
        # TODO: also, what if the scene removes the item early?
        self._scene.removeItem(self)

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


class _AnimatorCtrlr(QObject):
    def __init__(self, item: TmpAnimDisappearingRectItem) -> None:
        super().__init__()
        self.item = item

    _foo = -1.0  # unused, but the animator expects getter/setter

    @pyqtProperty(float)
    def foo(self) -> float:
        return self._foo

    @foo.setter  # type: ignore[no-redef]
    def foo(self, t: float) -> None:
        self.item.interp(t)
