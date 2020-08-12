# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QImage, QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItem, QGraphicsTextItem


class CommandMoveText(QUndoCommand):
    # Moves the textitem. we give it an ID so it can be merged with other
    # commandmoves on the undo-stack.
    # Don't use this for moving other graphics items
    # Graphicsitems are separate from graphicsTEXTitems
    def __init__(self, xitem, new_pos):
        super(CommandMoveText, self).__init__()
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
    def __init__(self, scene, blurb, ink):
        super(CommandText, self).__init__()
        self.scene = scene
        # set no interaction on scene's textitem - this avoids button-mashing
        # issues where text can be added during pasting in of text
        iflags = blurb.textInteractionFlags()
        blurb.setTextInteractionFlags(Qt.NoTextInteraction)
        # copy that textitem to one for this comment
        self.blurb = blurb
        # set the interaction flags back
        blurb.setTextInteractionFlags(iflags)
        # if the textitem has contents already then we
        # have to do some cleanup - give it focus and then
        # drop focus - correctly sets the text interaction flags
        if len(self.blurb.toPlainText()) > 0:
            QTimer.singleShot(1, self.blurb.setFocus)
            QTimer.singleShot(2, self.blurb.clearFocus)
            QTimer.singleShot(5, self.blurb.textToPng)
        self.setText("Text")

    def redo(self):
        self.blurb.flash_redo()
        self.scene.addItem(self.blurb)

    def undo(self):
        self.blurb.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.blurb))


class TextItem(QGraphicsTextItem):
    # Textitem is a qgraphicstextitem, has to handle
    # textinput and double-click to start editing etc.
    # Shift-return ends the editor
    def __init__(self, parent, fontsize=10):
        super(TextItem, self).__init__()
        self.saveable = True
        self.animator = [self]
        self.animateFlag = False
        self.parent = parent
        # Thick is thickness of bounding box hightlight used
        # to highlight the object when undo / redo happens.
        self.thick = 0
        self.setDefaultTextColor(Qt.red)
        self.setPlainText("")
        self.contents = ""
        self.font = QFont("Helvetica")
        self.font.setPointSizeF(fontsize)
        self.setFont(self.font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # Set it as editably with the text-editor
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        # Undo/redo animates via the thickness property
        self.anim = QPropertyAnimation(self, b"thickness")
        # for latex png
        self.state = "TXT"

    def getContents(self):
        if len(self.contents) == 0:
            return self.toPlainText()
        else:
            return self.contents

    def focusInEvent(self, event):
        if self.state == "PNG":
            self.pngToText()
        else:
            self.contents = self.toPlainText()
        super(TextItem, self).focusInEvent(event)

    def focusOutEvent(self, event):
        # When object loses the focus, need to make sure that
        # the editor stops, any highlighted text is released
        # and stops taking any text-interactions.
        tc = self.textCursor()
        tc.clearSelection()
        self.setTextCursor(tc)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        # if not PNG then update contents
        if self.state != "PNG":
            self.contents = self.toPlainText()
        super(TextItem, self).focusOutEvent(event)

    def textToPng(self):
        self.contents = self.toPlainText()
        if self.contents[:4].upper() == "TEX:":
            texIt = self.contents[4:]
        else:
            # is not latex so we don't have to PNG-it
            return

        fragfilename = self.parent.latexAFragment(texIt)
        if fragfilename:
            self.setPlainText("")
            tc = self.textCursor()
            qi = QImage(fragfilename)
            tc.insertImage(qi)
            self.state = "PNG"

    def pngToText(self):
        if self.contents != "":
            self.setPlainText(self.contents)
        self.state = "TXT"

    def keyPressEvent(self, event):
        # Shift-return ends the editor and releases the object
        if event.modifiers() == Qt.ShiftModifier and event.key() == Qt.Key_Return:
            # Clear any highlighted text and release.
            tc = self.textCursor()
            tc.clearSelection()
            self.setTextCursor(tc)
            self.setTextInteractionFlags(Qt.NoTextInteraction)
            self.contents = self.toPlainText()
            if self.contents[:4].upper() == "TEX:":
                self.textToPng()

        # control-return latexs the comment and replaces the text with the resulting image.
        # ends the editor.
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self.textToPng()
            tc = self.textCursor()
            tc.clearSelection()
            self.setTextCursor(tc)
            self.setTextInteractionFlags(Qt.NoTextInteraction)

        super(TextItem, self).keyPressEvent(event)

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            if self.group() is None:
                painter.setPen(QPen(QColor(255, 165, 0), 8))
                painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
                painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
                painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
                painter.drawRoundedRect(option.rect, 10, 10)
        else:
            # paint a bounding rectangle for undo/redo highlighting
            if self.thick > 0:
                painter.setPen(QPen(Qt.red, self.thick))
                painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(TextItem, self).paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsTextItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            # Notice that the value here is the new position, not the delta.
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)

    def flash_undo(self):
        # When undo-ing, draw a none->thick->none border around text.
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # When redo-ing, draw a none->med->none border around text.
        self.anim.setDuration(200)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(0)
        self.anim.start()

    def pickle(self):
        if len(self.contents) == 0:
            self.contents = self.toPlainText()
        return ["Text", self.contents, self.scenePos().x(), self.scenePos().y()]

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
    # Textitem is a qgraphicstextitem, has to handle
    # textinput and double-click to start editing etc.
    # Shift-return ends the editor
    def __init__(self, txt, fontsize=10):
        super(GhostText, self).__init__()
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(txt)
        self.font = QFont("Helvetica")
        self.font.setPointSizeF(fontsize)
        self.setFont(self.font)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        # Set it as editably with the text-editor
        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def changeText(self, txt):
        self.setPlainText(txt)
        if self.scene() is not None and txt[:4].upper() == "TEX:":
            texIt = (
                "\\color{blue}\n" + txt[4:].strip()
            )  # make color blue for ghost rendering
            fragfilename = self.scene().latexAFragment(texIt)
            if fragfilename:
                self.setPlainText("")
                tc = self.textCursor()
                qi = QImage(fragfilename)
                tc.insertImage(qi)
