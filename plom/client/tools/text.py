# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtGui import QFont, QImage, QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem, QGraphicsTextItem

from plom.client.tools import CommandTool, DeleteObject
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
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object
        self.xitem.setPos(self.new_pos)
        # Re-enable the item emitting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def undo(self):
        # Temporarily disable the item emitting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object back
        self.xitem.setPos(self.old_pos)
        # Re-enable the item emitting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

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
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)


class CommandText(CommandTool):
    def __init__(self, scene, pt, text):
        super().__init__(scene)
        self.blurb = TextItem(
            pt,
            text,
            fontsize=scene.fontSize,
            color=scene.style["annot_color"],
            _texmaker=scene,
        )
        self.do = DeleteObject(self.blurb.shape(), fill=True)
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

    def redo(self):
        self.scene.addItem(self.blurb)
        # update the deleteobject since the text may have been updated
        # use getshape - takes offset into account
        self.do.item.setPath(self.blurb.getShape())
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_redo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))

    def undo(self):
        self.scene.removeItem(self.blurb)
        # update the deleteobject since the text may have been updated
        # use getshape - takes offset into account
        self.do.item.setPath(self.blurb.getShape())
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))


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

    def __init__(self, pt, text, fontsize=10, color=Qt.red, _texmaker=None):
        super().__init__()
        self.saveable = True
        self._texmaker = _texmaker
        self.setDefaultTextColor(color)
        self.setPlainText(text)
        font = QFont("Helvetica")
        font.setPixelSize(round(fontsize))
        self.setFont(font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
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

    def enable_interactive(self):
        """Set it as editable with the text-editor."""
        self.setTextInteractionFlags(Qt.TextEditorInteraction)

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
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        super().focusOutEvent(event)

    def textToPng(self, force=False):
        """Try to switch to rendering via latex.

        args:
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
            tc = self.textCursor()
            qi = QImage(fragfilename)
            tc.insertImage(qi)

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
        if (
            event.modifiers() in (Qt.ShiftModifier, Qt.ControlModifier)
            and event.key() == Qt.Key_Return
        ):
            # Clear any highlighted text and release.
            tc = self.textCursor()
            tc.clearSelection()
            self.setTextCursor(tc)
            self.setTextInteractionFlags(Qt.NoTextInteraction)
            if event.modifiers() == Qt.ControlModifier:
                self.textToPng(force=True)
            else:
                self.textToPng()
        super().keyPressEvent(event)

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            if self.group() is None:  # make sure not part of a GDT
                painter.setPen(QPen(QColor(255, 165, 0), 8))
                painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
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

    def __init__(self, txt, fontsize, *, legal=True):
        super().__init__()
        if legal:
            self.setDefaultTextColor(Qt.blue)
        else:
            self.setDefaultTextColor(Qt.lightGray)
        self.setPlainText(txt)
        font = QFont("Helvetica")
        font.setPixelSize(round(fontsize))
        self.setFont(font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # If displaying png-rendered-latex, store the original text here
        self._tex_src_cache = None

    def is_rendered(self):
        """Is this TextItem displaying a PNG, e.g., of LaTeX?"""
        return self._tex_src_cache is not None

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
                tc = self.textCursor()
                qi = QImage(fragfilename)
                tc.insertImage(qi)
        if legal:
            self.setDefaultTextColor(Qt.blue)
        else:
            self.setDefaultTextColor(Qt.lightGray)
