# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QColor, QFont, QUndoCommand, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools import CommandTool
from plom.client.tools import log


# TODO: move this to move.py?
class CommandMoveText(QUndoCommand):
    # Moves the textitem. we give it an ID so it can be merged with other
    # commandmoves on the undo-stack.
    # Don't use this for moving other graphics items
    # Graphicsitems are separate from graphicsTEXTitems
    def __init__(self, xitem, new_pos):
        super().__init__()
        self.xitem = xitem
        self.old_pos = xitem.pos()
        self.new_pos = new_pos
        self.setText("MoveText")

    def id(self):
        # Give it an id number for merging of undo/redo commands
        return 102

    def redo(self):
        # Temporarily disable the item emitting "I've changed" signals
        self.xitem.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False
        )
        # Move the object
        self.xitem.setPos(self.new_pos)
        # Re-enable the item emitting "I've changed" signals
        self.xitem.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

    def undo(self):
        # Temporarily disable the item emitting "I've changed" signals
        self.xitem.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False
        )
        # Move the object back
        self.xitem.setPos(self.old_pos)
        # Re-enable the item emitting "I've changed" signals
        self.xitem.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

    def mergeWith(self, other):
        # Most commands cannot be merged - make sure the moved items are the
        # same - if so then merge things.
        if self.xitem != other.xitem:
            return False
        self.new_pos = other.new_pos
        return True


class UndoStackMoveTextMixin:
    # a mixin class to avoid copy-pasting this method over many *Item classes.
    # Overrides the itemChange method.
    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self.scene()
        ):
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)


class CommandText(CommandTool):
    def __init__(self, scene, pt, text):
        super().__init__(scene)
        self.blurb = TextItem(pt, text, style=scene.style, _texmaker=scene)
        # TODO: why do CommandText have a .blurb instead of a .obj?  Issue #3419.
        # HACK by just making another reference to it: else we need custom undo/redo
        self.obj = self.blurb
        self.setText("Text")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandText from a serialized form."""
        assert X[0] == "Text"
        X = X[1:]
        if len(X) != 3:
            raise ValueError("wrong length of pickle data")
        # knows to latex it if needed.
        return cls(scene, QPointF(X[1], X[2]), X[0])

    def get_undo_redo_animation_shape(self):
        # takes offset into account: always at origin without this
        return self.blurb.getShape()


class TextItem(UndoStackMoveTextMixin, QGraphicsTextItem):
    """A multiline text annotation with optional LaTeX rendering.

    Textitem has to handle textinput.  Shift-return ends the editor.
    Ctrl-return ends the editor and forces LaTeX rendering by prepending
    with `tex:`.

    Has special handling for text that begins with `tex:` which is rendered
    to an image using LaTeX via a call to the server.  A TextItem knows
    whether it is displaying source text or rendered text: query the
    `is_rendered()` method.

    The TextItem is built with no text-field interaction (editor) disabled.
    Call `enable_interactive()` to enable it: if you also want the editor
    to open right away, call `setFocus()`.

    `_texmaker` is a workaround: we don't have a scene yet but some callers
    (GDTI!) will expect us to render tex immediately.  If so they will need
    to give us PageScene here.
    TODO: try to remove this with some future refactor?
    """

    def __init__(
        self,
        pt,
        text: str,
        *,
        style: dict[str, Any],
        _texmaker=None,
    ):
        super().__init__()
        self.saveable = True
        self._texmaker = _texmaker
        self.setDefaultTextColor(style["annot_color"])
        self.setPlainText(text)
        font = QFont("Helvetica")
        self.annot_scale = style["scale"]
        font.setPixelSize(round(style["fontsize"]))
        self.setFont(font)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setPos(pt)
        # If displaying png-rendered-latex, store the original text here
        self._tex_src_cache = None
        if text.casefold().startswith("tex:"):
            # TODO: Issue #1624: this is causing two API rendering calls
            # self.textToPng()
            # instead, hide latency of API call: meanwhile source text displayed
            # Issue #1391: unfortunately causes a race, at least in randomarker
            QTimer.singleShot(5, self.textToPng)

    def getShape(self):
        # returns shape, but with offset
        shp = self.shape()
        shp.translate(self.pos())
        return shp

    def set_image(self, image_path: str) -> None:
        """Replace the current content with an image.

        Args:
            image_path: image path.
            fontsize: scene's fontsize which will be used to scale the image.
        """
        pixmap = QPixmap(image_path)
        original_width = pixmap.width()
        original_height = pixmap.height()

        scaled_width = int(original_width * self.annot_scale)
        scaled_height = int(original_height * self.annot_scale)

        html_content = f"""
        <div style="text-align: center;">
            <img src="{image_path}" width="{scaled_width}" height="{scaled_height}" style="vertical-align: middle;" />
        </div>
        """
        self.setHtml(html_content)

    def enable_interactive(self):
        """Set it as editable with the text-editor."""
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)

    def is_rendered(self):
        """Is this TextItem displaying a rendering of LaTeX?

        Returns:
            bool: True if currently showing a rendering (such as an
                png image) or False if displaying either plain text or
                the source text of what could be rendered.
        """
        return self._tex_src_cache is not None

    def restyle(self, style):
        self.setDefaultTextColor(style["annot_color"])
        if self.is_rendered():
            self.retex()

    def retex(self):
        self.pngToText()
        self.textToPng()

    def toPlainText(self):
        """The text itself or underlying source if displaying latex."""
        if self.is_rendered():
            return self._tex_src_cache
        return super().toPlainText()

    def focusInEvent(self, event):
        """On focus, we switch back to source/test mode."""
        if self.is_rendered():
            self.pngToText()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        # When object loses the focus, need to make sure that
        # the editor stops, any highlighted text is released
        # and stops taking any text-interactions.
        tc = self.textCursor()
        tc.clearSelection()
        self.setTextCursor(tc)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        super().focusOutEvent(event)

    def textToPng(self, force=False):
        """Try to switch to rendering via latex.

        Args:
            force (bool): If True, add the `tex:` prefix if not present.
        """
        if self.is_rendered():
            return
        src = self.toPlainText()
        if not src.casefold().startswith("tex:"):
            if force:
                src = "tex: " + src
            else:
                return
        texIt = src[4:].strip()

        # TODO: maybe nicer/more generally useful to provide access to preamble
        c = self.defaultTextColor().getRgb()

        assert len(c) == 4
        if c != (255, 0, 0, 255):
            # Careful: red is default, using this would cause a cache miss
            # TODO: maybe its nicer to pass the colour to latexAFragment?
            texIt = (
                r"\definecolor{annot}{RGB}{"
                + ",".join(str(x) for x in c[:3])
                + "}\n"
                + "\\color{annot}\n"
                + texIt
            )
        # In theory this can be self.scene() like elsewhere but it seems
        # this gets called before we have a scene (e.g., from Rubric GDTI)
        # so we awkwardly pass the scene around as `._texmaker`.
        if not self.scene():
            log.warning(
                "TextItem needs to tex but does not yet have a scene, probably came from rubric placement?"
            )
            # This is associated with some QTimer nonsense, see #2188 and #1624
            # TODO: at least do it quietly without popping a duplicate dialog
            fragfilename = self._texmaker.latexAFragment(
                texIt, quiet=True, cache_invalid_tryagain=True
            )
        else:
            fragfilename = self.scene().latexAFragment(
                texIt, quiet=False, cache_invalid_tryagain=True
            )
        if fragfilename:
            self._tex_src_cache = src
            self.setPlainText("")
            self.set_image(fragfilename)

    def pngToText(self):
        """If displaying rendered latex, switch back to source."""
        if self.is_rendered():
            self.setPlainText(self._tex_src_cache)
        self._tex_src_cache = None

    def keyPressEvent(self, event):
        """Shift/Ctrl-Return ends the editor, and renders with latex.

        Shift-Return will render if the string starts with the magic
        prefix `tex:`.  Ctrl-Return adds the prefix if necessary.
        """
        if event.modifiers() in (
            Qt.KeyboardModifier.ShiftModifier,
            Qt.KeyboardModifier.ControlModifier,
        ) and (event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter):
            # Clear any highlighted text and release.
            tc = self.textCursor()
            tc.clearSelection()
            self.setTextCursor(tc)
            self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.textToPng(force=True)
            else:
                self.textToPng()
        super().keyPressEvent(event)

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            if self.group() is None:  # make sure not part of a GDT
                painter.setPen(OutOfBoundsPen)
                painter.setBrush(OutOfBoundsFill)
                painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
                painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
                painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super().paint(painter, option, widget)

    def pickle(self):
        src = self.toPlainText()
        return ["Text", src, self.scenePos().x(), self.scenePos().y()]


class GhostText(QGraphicsTextItem):
    """Blue "ghost" of text indicating what text will be placed in scene."""

    def __init__(self, txt: str, annot_scale: float, fontsize: int, *, legal=True):
        super().__init__()
        if legal:
            self.setDefaultTextColor(QColor("blue"))
        else:
            self.setDefaultTextColor(QColor("lightGray"))
        self.setPlainText(txt)
        font = QFont("Helvetica")
        font.setPixelSize(round(fontsize))
        self.setFont(font)
        self.setOpacity(0.7)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        # If displaying png-rendered-latex, store the original text here
        self._tex_src_cache = None

    def update_annot_scale(self, annot_scale: float) -> None:
        """Update the annotation scale being used.

        Args:
            annot_scale: scene's global annotation scale.
        """
        self.annot_scale = annot_scale

    def set_image(self, image_path: str) -> None:
        """Replace the current content with an image.

        Args:
            image_path: image path.
        """
        pixmap = QPixmap(image_path)
        original_width = pixmap.width()
        original_height = pixmap.height()

        scaled_width = int(original_width * self.annot_scale)
        scaled_height = int(original_height * self.annot_scale)

        html_content = f"""
        <div style="text-align: center;">
            <img src="{image_path}" width="{scaled_width}" height="{scaled_height}" style="vertical-align: middle;" />
        </div>
        """
        self.setHtml(html_content)

    def is_rendered(self):
        """Is this TextItem displaying a PNG, e.g., of LaTeX?"""
        return self._tex_src_cache is not None

    def toPlainText(self):
        """The text itself or underlying source if displaying latex."""
        if self.is_rendered():
            return self._tex_src_cache
        return super().toPlainText()

    def changeText(self, txt, legal):
        self._tex_src_cache = None
        self.setPlainText(txt)
        if self.scene() and txt.casefold().startswith("tex:"):
            if legal:
                texIt = (
                    "\\color{blue}\n" + txt[4:].strip()
                )  # make color blue for ghost rendering
            else:
                texIt = (
                    "\\color{gray}\n" + txt[4:].strip()
                )  # make color gray for ghost rendering (when delta not legal)

            fragfilename = self.scene().latexAFragment(texIt, quiet=True)
            if fragfilename:
                self._tex_src_cache = txt
                self.setPlainText("")
                self.set_image(fragfilename)
        if legal:
            self.setDefaultTextColor(QColor("blue"))
        else:
            self.setDefaultTextColor(QColor("lightGray"))
