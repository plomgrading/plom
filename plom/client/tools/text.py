# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QImage, QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem, QGraphicsTextItem


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
        # Temporarily disable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object
        self.xitem.setPos(self.new_pos)
        # Reenable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def undo(self):
        # Temporarily disable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object back
        self.xitem.setPos(self.old_pos)
        # Reenable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def mergeWith(self, other):
        # Most commands cannot be merged - make sure the moved items are the
        # same - if so then merge things.
        if self.xitem != other.xitem:
            return False
        self.new_pos = other.new_pos
        return True


class CommandText(QUndoCommand):
    def __init__(self, scene, pt, text):
        super().__init__()
        self.scene = scene
        self.blurb = TextItem(
            pt, text, scene, fontsize=scene.fontSize, color=scene.style["annot_color"]
        )
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
        self.blurb.flash_redo()
        self.scene.addItem(self.blurb)

    def undo(self):
        self.blurb.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.blurb))


class TextItem(QGraphicsTextItem):
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
    """

    def __init__(self, pt, text, parent, fontsize=10, color=Qt.red):
        super().__init__()
        self.saveable = True
        self.animator = [self]
        self.animateFlag = False
        # TODO: really this is PageScene or Marker: someone who can TeX for us
        # TODO: its different from e.g., BoxItem (where parent is the animator)
        self.parent = parent
        # Thick is thickness of bounding box hightlight used
        # to highlight the object when undo / redo happens.
        self.thick = 0
        self.setDefaultTextColor(color)
        self.setPlainText(text)
        font = QFont("Helvetica")
        font.setPointSizeF(fontsize)
        self.setFont(font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # Undo/redo animates via the thickness property
        self.anim = QPropertyAnimation(self, b"thickness")
        self.setPos(pt)
        # If displaying png-rendered-latex, store the original text here
        self._tex_src_cache = None
        if text.casefold().startswith("tex:"):
            # self.textToPng()
            # instead, hide latency of API call: meanwhile source text displayed
            # Issue #1391: unfortunately causes a race, at least in randomarker
            QTimer.singleShot(5, self.textToPng)

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

    def getContents(self):
        """Older, maybe deprecated way of getting the text/source."""
        return self.toPlainText()

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
        if c != (255, 0, 0, 0):
            # Careful: red is default, using this would cause a cache miss
            # TODO: maybe its nicer to pass the colour to latexAFragment?
            texIt = (
                r"\definecolor{annot}{RGB}{"
                + ",".join(str(x) for x in c[:3])
                + "}\n"
                + "\\color{annot}\n"
                + texIt
            )
        fragfilename = self.parent.latexAFragment(texIt)
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
        else:
            # paint a bounding rectangle for undo/redo highlighting
            if self.thick > 0:
                painter.setPen(QPen(self.defaultTextColor(), self.thick))
                painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsTextItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            # Notice that the value here is the new position, not the delta.
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def flash_undo(self):
        """Undo animation: thin -> thick -> none border around text"""
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)  # TODO: should be 4*style["pen_width"]
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin border around text."""
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 4)  # TODO: should be 2*style["pen_width"]
        self.anim.setEndValue(0)
        self.anim.start()

    def pickle(self):
        src = self.toPlainText()
        return ["Text", src, self.scenePos().x(), self.scenePos().y()]

    # For the animation of border
    @pyqtProperty(int)
    def thickness(self):
        return self.thick

    # For the animation of border
    @thickness.setter
    def thickness(self, value):
        self.thick = value
        self.update()


class GhostText(QGraphicsTextItem):
    """Blue "ghost" of text indicating what text will be placed in scene."""

    def __init__(self, txt, fontsize=10):
        super().__init__()
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(txt)
        font = QFont("Helvetica")
        font.setPointSizeF(fontsize)
        self.setFont(font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # If displaying png-rendered-latex, store the original text here
        self._tex_src_cache = None

    def is_rendered(self):
        """Is this TextItem displaying a PNG, e.g., of LaTeX?"""
        return self._tex_src_cache is not None

    def changeText(self, txt):
        self._tex_src_cache = None
        self.setPlainText(txt)
        if self.scene() and txt.casefold().startswith("tex:"):
            texIt = (
                "\\color{blue}\n" + txt[4:].strip()
            )  # make color blue for ghost rendering
            fragfilename = self.scene().latexAFragment(texIt)
            if fragfilename:
                self._tex_src_cache = txt
                self.setPlainText("")
                tc = self.textCursor()
                qi = QImage(fragfilename)
                tc.insertImage(qi)
