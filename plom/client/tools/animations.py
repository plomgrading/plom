# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QObject
from PyQt6.QtCore import QPropertyAnimation, QAbstractAnimation
from PyQt6.QtCore import pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtWidgets import QGraphicsRectItem

from plom.client.tools import log
from plom.client.tools import AnimationDuration


# Note: tried multiple inheritance to make this an Object, like:
#     TmpAnimRectItem(QGraphicsRectItem, QObject):
# In theory, this allows QPropertyAnimation to talk to self, but it just
# crashes for me.  Also tried swapping the order of inheritance.
# There is also a QGraphicsItemAnimations but its deprecated.
# Our workaround is the above `_AnimatorCtrlr` class, which exists
# just to call back to this one.
class TmpAnimItem(QGraphicsRectItem):
    """A base class for new-style animations.

    At the end of your ``__init__`` function you must start the animation
    by calling `self.start()`.

    Instance variables:
        anim: a QPropertyAnimation, you can call `setDuration` to change
            the time from default.  It has default `setStartValue` of 0,
            `setEndValue` of 1.
    """

    def __init__(self, scene) -> None:
        super().__init__()
        self._scene = scene
        self.saveable = False

        # Crashes when calling our methods (probably b/c QGraphicsItem
        # is not QObject).  Instead we use a helper class.  "t" is a
        # property of that class, which the QPropertyAnimation will
        # set between 0 and 1 as it wishes.
        self._ctrlr = _AnimatorCtrlr(self)
        self.anim = QPropertyAnimation(self._ctrlr, b"t")

        self.anim.setDuration(AnimationDuration)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)

        # When the animation finishes, it will destroy itself, whence
        # we'll get a callback to remove ourself from the scene
        self.anim.destroyed.connect(self.remove_from_scene)

    def start(self):
        self.anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def remove_from_scene(self) -> None:
        log.debug(f"TmpAnimItem: removing {self} from scene")
        # TODO: can we be sure that scene survives until the end of the animation?
        # TODO: also, what if the scene removes the item early?
        self._scene.removeItem(self)

    def interp(self, t: float) -> None:
        raise NotImplementedError(
            "you must implement a interp method for your subclass"
        )


class _AnimatorCtrlr(QObject):

    _t = -1.0  # unused, but the animator expects getter/setter

    def __init__(self, item: TmpAnimItem) -> None:
        super().__init__()
        self.item = item

    @pyqtProperty(float)
    def t(self) -> float:
        return self._t

    @t.setter  # type: ignore[no-redef]
    def t(self, value: float) -> None:
        self.item.interp(value)
