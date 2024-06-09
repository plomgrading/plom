# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QRectF, QObject
from PyQt6.QtCore import QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QBrush, QColor, QPen, QUndoCommand
from PyQt6.QtWidgets import QGraphicsRectItem


# how long animations take in milliseconds
Duration = 200


class CommandRotatePage(QUndoCommand):
    """Do or undo a rotation of a page, not including cleanup moves of annotations."""

    def __init__(self, scene, page_image_idx: int, degrees: int) -> None:
        # scene type is plom.client.pagescene.PageScene
        super().__init__()
        self.scene = scene
        self.page_image_idx = page_image_idx
        self.degrees = degrees
        self.do = _Animator(
            degrees, scene.underImage.images[page_image_idx].boundingRect()
        )
        self.setText("RotatePage")

    def redo(self):
        # TODO: is this the correct boundary?
        img = self.scene.underImage.images[self.page_image_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._rotate_page_image_only(self.page_image_idx, self.degrees)
        img = self.scene.underImage.images[self.page_image_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_redo(self.degrees, r1, r2)
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(self.do.item))

    def undo(self):
        img = self.scene.underImage.images[self.page_image_idx]
        r1 = img.mapRectToScene(img.boundingRect())
        self.scene._rotate_page_image_only(self.page_image_idx, -self.degrees)
        img = self.scene.underImage.images[self.page_image_idx]
        r2 = img.mapRectToScene(img.boundingRect())
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_undo(self.degrees, r2, r1)
        QTimer.singleShot(Duration, lambda: self.scene.removeItem(self.do.item))


class _Animator(QObject):
    def __init__(self, degrees, r):
        super().__init__()
        self.degrees = degrees
        self.item = DeleteItem(QRectF(10, 10, 1200, 2000))
        # self.item = DeleteItem(r.adjusted(100, 100, -100, -100))
        self.anim = QPropertyAnimation(self, b"foo")
        self.anim.setDuration(Duration)

    def flash_undo(self, degrees, r1, r2):
        self.r1 = r1
        self.r2 = r2
        self.degrees = degrees
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

    def flash_redo(self, degrees, r1, r2):
        self.r1 = r1
        self.r2 = r2
        self.degrees = degrees
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

    _foo = -1.0  # unused, but the animator expects getter/setter

    @pyqtProperty(float)
    def foo(self) -> float:
        return self._foo

    @foo.setter  # type: ignore[no-redef]
    def foo(self, t: float) -> float:
        r1 = self.r1
        r2 = self.r2
        p = t * r1.center() + (1 - t) * r2.center()
        angle = t * self.degrees
        # TODO: r = t*r1 + (1-t)*r2
        # self.item.setRect(r)
        w = min(r1.width(), r1.height(), r2.width(), r2.height()) / 4
        # 2*w size decreasing to w, then back up to 2*w
        w = w + w * (2 * t - 1) ** 2
        self.item.setRect(p.x() - w, p.y() - w, 2 * w, 2 * w)
        self.item.setTransformOriginPoint(self.item.boundingRect().center())
        self.item.setRotation(angle)


# class TmpAnimatingRectItem
class DeleteItem(QGraphicsRectItem):
    def __init__(self, r):
        super().__init__()
        self.saveable = False
        self.setRect(r)
        self.setPen(QPen(QColor(8, 232, 222, 128), 10))
        self.setBrush(QBrush(QColor(8, 232, 222, 16)))
