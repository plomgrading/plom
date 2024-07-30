# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021, 2023-2024 Colin B. Macdonald

from PyQt6.QtGui import QPainterPath, QUndoCommand

from .animations import AnimatingTempPathItem, AnimatingTempItemMixin


class CommandTool(QUndoCommand):
    """Handles the do/undo of edits to the PageScene.

    Subclasses will implement the ``obj`` which is the actual object to be
    drawn.  Commands are free to subclass ``QUndoCommand`` themselves
    rather than subclassing this ``CommandTool``.

    The :py:method:`redo` method handles both the initial drawing and any
    subsequent draw operations to due to undo/redo cycles.

    Thus far, the ``redo`` method should not create subcommand objects:
    in my experience, hard to debug and segfault behaviour comes from
    trying.  Instead, macros are instead created in PageScene.  This
    could be revisited in the future.
    """

    def __init__(self, scene) -> None:
        super().__init__()
        self.scene = scene
        # obj needs to be done by each tool
        # self.obj = QGraphicsItem()

    def get_undo_redo_animation_shape(self) -> QPainterPath:
        """Return a shape appropriate for animating the undo/redo of an object.

        Returns:
            A QPainterPath used to draw the undo and redo temporary animations.
            Subclasses are free to return a different, perhaps simpler
            QPainterPath.  For example, :py:class:`CommandHighlight` returns
            its ``obj._original_path`` instead.  Another example would be a subclass
            that does not use the ``.obj`` instantance variable.
        """
        return self.obj.shape()

    def get_undo_redo_animation(
        self, *, backward: bool = False
    ) -> AnimatingTempItemMixin:
        """Return an object suitable for animating the undo/redo action.

        Returns:
            A QGraphicsItem, that also has the AnimatingTempItemMixin.
            This is a special object that will animate and then remove
            itself from the scene.
        """
        return AnimatingTempPathItem(
            self.get_undo_redo_animation_shape(), backward=backward
        )

    def redo_animation(self) -> None:
        """An animation of redoing something."""
        self.scene.addItem(self.get_undo_redo_animation())

    def redo(self) -> None:
        """Redo a command, putting it back in the scene with an animation."""
        self.scene.addItem(self.obj)
        self.redo_animation()

    def undo_animation(self) -> None:
        """An animation of undoing something."""
        self.scene.addItem(self.get_undo_redo_animation(backward=True))

    def undo(self) -> None:
        """Undo a command, removing from the scene with an animation."""
        self.scene.removeItem(self.obj)
        self.undo_animation()
