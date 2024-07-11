# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from PyQt6.QtCore import QObject
from PyQt6.QtCore import QPropertyAnimation, QAbstractAnimation
from PyQt6.QtCore import pyqtProperty  # type: ignore[attr-defined]
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsPathItem

from plom.client.tools import log


# rough length of animations take in milliseconds: some might be shorter,
# some longer but they will be scaled by this value.
AnimationDuration: int = 200

AnimationPenColour = QColor(8, 232, 222, 128)
AnimationPenThickness = 8
AnimationFillColour = QColor(8, 232, 222, 16)


# Note: tried multiple inheritance to make this an Object, like:
#     TmpAnimRectItem(QGraphicsRectItem, QObject):
# In theory, this allows QPropertyAnimation to talk to self, but it just
# crashes for me.  Also tried swapping the order of inheritance.
# There is also a QGraphicsItemAnimations but its deprecated.
# Our workaround is the above `_AnimatorCtrlr` class, which exists
# just to call back to this one.
class AnimatingTempItemMixin:
    """A base class for new-style animations.

    At the end of your ``__init__`` function you must start the animation
    by calling `self.start()`.

    Instance variables:
        anim: a QPropertyAnimation, you can call `setDuration` to change
            the time from default.  It has default `setStartValue` of 0,
            `setEndValue` of 1.
    """

    is_transcient_animation = True

    def anim_init(self) -> None:
        """Initialize the animation, basically this is the init method.

        But the author doesn't grok multiple inheritance enough to do
        it like that so this has a special name but is to be called
        in the class this mixin is mixed into.  It should be followed
        by a call to :method:`start`.
        """
        self.saveable = False

        # Crashes when calling our methods (probably b/c QGraphicsItem
        # is not QObject).  Instead we use a helper class.  "prop" is a
        # property of that class, which the QPropertyAnimation will
        # set between 0 and 1 as it wishes.  "prop" will eventually
        # be passed back to ``interp`` (the "t" arg).
        self._ctrlr = _AnimatorCtrlr(self)
        self.anim = QPropertyAnimation(self._ctrlr, b"prop")

        self.anim.setDuration(AnimationDuration)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)

        # When the animation finishes, it will destroy itself, whence
        # we'll get a callback to remove ourself from the scene
        self.anim.destroyed.connect(self.remove_from_scene)

    def start(self):
        """Start the animation, to be called at the end of init."""
        self.anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def remove_from_scene(self) -> None:
        """Remove this item from the scene."""
        # Classes this is mixed into must have a `scene` method
        scene = self.scene()  # type: ignore[attr-defined]
        if scene is None:
            # its already been removed, or maybe the scene did not survive until
            # the end of the animation
            log.debug(f"TmpAnimItem: {self} was already scene-less")
            return
        log.debug(f"TmpAnimItem: removing {self} from scene")
        scene.removeItem(self)

    def interp(self, t: float) -> None:
        raise NotImplementedError(
            "you must implement a interp method for your subclass"
        )


class _AnimatorCtrlr(QObject):
    _prop = -1.0  # unused, but the animator expects getter/setter

    def __init__(self, item: AnimatingTempItemMixin) -> None:
        super().__init__()
        self.item = item

    @pyqtProperty(float)
    def prop(self) -> float:
        return self._prop

    @prop.setter  # type: ignore[no-redef]
    def prop(self, value: float) -> None:
        self.item.interp(value)


# Note multiple inheritance with PyQt is ok as long as only one is a Qt class
class AnimatingTempRectItemABC(QGraphicsRectItem, AnimatingTempItemMixin):
    """An abstract base class for new-style animated rectangles.

    At the end of your ``__init__`` function you must start the animation
    by calling `self.start()`.

    You'll need to subclass this, and add a ``interp`` method.

    Instance variables:
        anim: a QPropertyAnimation, you can call `setDuration` to change
            the time from default.  It has default `setStartValue` of 0,
            `setEndValue` of 1.
    """

    def __init__(self) -> None:
        super().__init__()
        self.anim_init()
        self.setPen(QPen(AnimationPenColour, AnimationPenThickness))
        self.setBrush(QBrush(AnimationFillColour))


class AnimatingTempPathItem(QGraphicsPathItem, AnimatingTempItemMixin):
    """New-style animated path.

    You can use this as-is, to animate the thickness of the path.

    If you subclass this, call the superclass ``__init__`` like this:
    ``super().__init__(start=False)``.
    Then at the end of your ``__init__`` function you must start the
    animation by calling `self.

    Instance variables:
        anim: a QPropertyAnimation, you can call `setDuration` to change
            the time from default.  It has default `setStartValue` of 0,
            `setEndValue` of 2.
    """

    def __init__(self, path, backward: bool = False, start: bool = True) -> None:
        super().__init__()
        self.anim_init()
        self.setPath(path)
        self.setPen(QPen(AnimationPenColour, AnimationPenThickness))
        if backward:
            self.anim.setStartValue(AnimationPenThickness / 4.0)
            self.anim.setEndValue(0)
        else:
            self.anim.setStartValue(0)
            self.anim.setEndValue(AnimationPenThickness / 4.0)
        self.anim.setKeyValueAt(0.5, AnimationPenThickness)
        if start:
            self.start()

    def interp(self, thickness: float):
        self.setPen(QPen(AnimationPenColour, thickness))
