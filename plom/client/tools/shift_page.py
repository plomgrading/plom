# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF, QObject, QTimer, QPropertyAnimation
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
        # animation showing what happened
        do = _Animator()
        self.scene.addItem(do.item)
        do.flash_redo(r1, r2)
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(do.item))

    def undo(self):
        img = self.scene.underImage.images[self.old_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._shift_page_image_only(self.new_idx, self.old_idx)
        img = self.scene.underImage.images[self.new_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # animation showing what happened
        do = _Animator()
        self.scene.addItem(do.item)
        do.flash_undo(r1, r2)
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(do.item))


# TODO: I thought I could subclass the QGraphicsRectItem too, but segfaults
# maybe PyQt does not support multiple inheritance as the Qt C++ docs suggest?
class _Animator(QObject):
    def __init__(self):
        super().__init__()
        self.item = TmpAnimatingRectItem(QRectF(10, 10, 20, 20))
        self.anim = QPropertyAnimation(self, b"foo")
        self.anim.setDuration(Duration)

    def flash_undo(self, r1, r2):
        self.r1 = r1
        self.r2 = r2
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def flash_redo(self, r1, r2):
        self.r1 = r1
        self.r2 = r2
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

    _foo = -1.0  # unused, but the animator expects getter/setter

    @pyqtProperty(float)
    def foo(self) -> float:
        return self._foo

    @foo.setter  # type: ignore[no-redef]
    def foo(self, t: float) -> None:
        r1 = self.r1
        r2 = self.r2
        p = t * r1.center() + (1 - t) * r2.center()
        # TODO: r = t*r1 + (1-t)*r2
        # self.item.setRect(r)
        w = min(r1.width(), r1.height(), r2.width(), r2.height()) / 4
        # 2*w size decreasing to w, then back up to 2*w
        w = w + w * (2 * t - 1) ** 2
        self.item.setRect(p.x() - w, p.y() - w, 2 * w, 2 * w)


class TmpAnimatingRectItem(QGraphicsRectItem):
    def __init__(self, r):
        super().__init__()
        self.saveable = False
        self.setRect(r)
        self.setPen(QPen(QColor(8, 232, 222, 128), 10))
        self.setBrush(QBrush(QColor(8, 232, 222, 16)))
