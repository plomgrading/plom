# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF, QObject
from PyQt6.QtCore import QPropertyAnimation, QAbstractAnimation
from PyQt6.QtCore import pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtGui import QBrush, QColor, QPen, QUndoCommand
from PyQt6.QtWidgets import QGraphicsRectItem


# how long animations take in milliseconds
Duration = 200


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
        self.scene.addItem(TmpAnimRectItem(self.scene, r1, r2))

    def undo(self):
        img = self.scene.underImage.images[self.old_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._shift_page_image_only(self.new_idx, self.old_idx)
        img = self.scene.underImage.images[self.new_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # temporary animation, removes itself when done
        self.scene.addItem(TmpAnimRectItem(self.scene, r2, r1))


# TODO: I thought I could subclass the QGraphicsRectItem too, but segfaults
# maybe PyQt does not support multiple inheritance as the Qt C++ docs suggest?
class _AnimatorCtrlr(QObject):
    def __init__(self, item):
        super().__init__()
        self.item = item

    _foo = -1.0  # unused, but the animator expects getter/setter

    @pyqtProperty(float)
    def foo(self) -> float:
        return self._foo

    @foo.setter  # type: ignore[no-redef]
    def foo(self, t: float) -> None:
        self.item.interp(t)


class TmpAnimRectItem(QGraphicsRectItem):
    def __init__(self, scene, r1, r2):
        super().__init__()
        self._scene = scene
        self.saveable = False
        self.setRect(r1)
        self.setPen(QPen(QColor(8, 232, 222, 128), 10))
        self.setBrush(QBrush(QColor(8, 232, 222, 16)))
        self.r1 = r1
        self.r2 = r2
        # Crashes when calling our methods (probably b/c QGraphicsItem
        # is not QObject).  Instead we use a helper class.
        self._ctrlr = _AnimatorCtrlr(self)
        self.anim = QPropertyAnimation(self._ctrlr, b"foo")
        self.anim.setDuration(Duration)
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        # When the animation finishes, it will destroy itself, whence
        # we'll get a callback to remove ourself from the scene
        self.anim.destroyed.connect(self.remove_from_scene)
        self.anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def interp(self, t: float) -> None:
        """Draw a rectangle part way between r1 and r2.

        This includes a zoom out effect but currently does strictly speaking
        interpolate r1 and r2 directly.
        """
        r1 = self.r1
        r2 = self.r2
        p = t * r1.center() + (1 - t) * r2.center()
        # TODO: r = t*r1 + (1-t)*r2
        # self.setRect(r)
        w = min(r1.width(), r1.height(), r2.width(), r2.height()) / 4
        # 2*w size decreasing to w, then back up to 2*w
        w = w + w * (2 * t - 1) ** 2
        self.setRect(p.x() - w, p.y() - w, 2 * w, 2 * w)

    def remove_from_scene(self) -> None:
        print(f"TmpAnimItem: removing {self} from scene")
        # TODO: can we be sure that scene survives until the end of the animation?
        self._scene.removeItem(self)
