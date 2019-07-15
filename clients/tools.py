__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json
from math import sqrt
from PyQt5.QtCore import Qt, QLineF, QPointF, pyqtProperty, QPropertyAnimation, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsItemGroup,
    QGraphicsObject,
    QGraphicsTextItem,
    QUndoCommand,
)


# Commands for the undo stack
# Each command needs init, redo and undo
# To highlight objects when created / destroyed they
# run a simple animation.
# The arrow is very typical
class CommandArrow(QUndoCommand):
    # Command to create/remove an arrow object
    def __init__(self, scene, pti, ptf):
        super(CommandArrow, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        # create an arrow item
        self.arrowItem = ArrowItemObject(self.pti, self.ptf)
        self.setText("Arrow")

    def redo(self):
        # arrow item knows how to highlight on undo and redo.
        self.arrowItem.flash_redo()
        self.scene.addItem(self.arrowItem.ai)

    def undo(self):
        # the undo animation takes 0.5s
        # so trigger its removal after 0.5s.
        self.arrowItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.arrowItem.ai))


class CommandBox(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, rect):
        super(CommandBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.boxItem = BoxItemObject(self.rect)
        self.setText("Box")

    def redo(self):
        self.boxItem.flash_redo()
        self.scene.addItem(self.boxItem.bi)

    def undo(self):
        self.boxItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.boxItem.bi))


class CommandCross(QUndoCommand):
    # Very similar to CommandArrow.
    def __init__(self, scene, pt):
        super(CommandCross, self).__init__()
        self.scene = scene
        self.pt = pt
        self.crossItem = CrossItemObject(self.pt)
        self.setText("Cross")

    def redo(self):
        self.crossItem.flash_redo()
        self.scene.addItem(self.crossItem.ci)

    def undo(self):
        self.crossItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.crossItem.ci))


class CommandDelta(QUndoCommand):
    # Very similar to CommandArrow
    # But must send a "the total mark has changed" signal
    def __init__(self, scene, pt, delta, fontsize):
        super(CommandDelta, self).__init__()
        self.scene = scene
        self.delta = delta
        self.pt = pt
        self.delItem = DeltaItem(pt, self.delta, fontsize)
        self.setText("Delta")

    def redo(self):
        self.delItem.flash_redo()
        self.scene.addItem(self.delItem)
        # Emit a markChangedSignal for the marker to pick up and change total.
        # Mark increased by delta
        self.scene.markChangedSignal.emit(self.delta)

    def undo(self):
        self.delItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.delItem))
        # Emit a markChangedSignal for the marker to pick up and change total.
        # Mark decreased by delta
        self.scene.markChangedSignal.emit(-self.delta)


class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a delta-item which changes the current mark
    def __init__(self, scene, deleteItem, pt):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.pt = pt
        self.setText("Delete")

    def redo(self):
        # If the object is a DeltaItem then emit a mark-changed signal.
        if isinstance(self.deleteItem, DeltaItem):
            # Mark decreases by delta
            self.scene.markChangedSignal.emit(-self.deleteItem.delta)
        self.scene.removeItem(self.deleteItem)

    def undo(self):
        # If the object is a DeltaItem then emit a mark-changed signal.
        if isinstance(self.deleteItem, DeltaItem):
            # Mark increases by delta
            self.scene.markChangedSignal.emit(self.deleteItem.delta)
        self.scene.addItem(self.deleteItem)


class CommandHighlight(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandHighlight, self).__init__()
        self.scene = scene
        self.path = path
        self.highLightItem = HighLightItemObject(self.path)
        self.setText("Highlight")

    def redo(self):
        self.highLightItem.flash_redo()
        self.scene.addItem(self.highLightItem.hli)

    def undo(self):
        self.highLightItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.highLightItem.hli))


class CommandLine(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        # A line from pti(nitial) to ptf(inal)
        self.lineItem = LineItemObject(self.pti, self.ptf)
        self.setText("Line")

    def redo(self):
        self.lineItem.flash_redo()
        self.scene.addItem(self.lineItem.li)

    def undo(self):
        self.lineItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.lineItem.li))


class CommandMoveItem(QUndoCommand):
    # Moves the graphicsitem. we give it an ID so it can be merged with other
    # commandmoves on the undo-stack.
    # Don't use this for moving text - that gets its own command.
    # Graphicsitems are separate from graphicsTEXTitems
    def __init__(self, xitem, delta):
        super(CommandMoveItem, self).__init__()
        # The item to move
        self.xitem = xitem
        # The delta-position of that item.
        self.delta = delta
        self.setText("Move")

    def id(self):
        # Give it an id number for merging of undo/redo commands
        return 101

    def redo(self):
        # Temporarily disable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object
        self.xitem.setPos(self.xitem.pos() + self.delta)
        # Reenable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def undo(self):
        # Temporarily disable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        # Move the object back
        self.xitem.setPos(self.xitem.pos() - self.delta)
        # Reenable the item emiting "I've changed" signals
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def mergeWith(self, other):
        # Most commands cannot be merged - make sure the moved items are the
        # same - if so then merge things.
        if self.xitem != other.xitem:
            return False
        self.delta = other.delta
        return True


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


class CommandPen(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandPen, self).__init__()
        self.scene = scene
        self.path = path
        self.penItem = PenItemObject(self.path)
        self.setText("Pen")

    def redo(self):
        self.penItem.flash_redo()
        self.scene.addItem(self.penItem.pi)

    def undo(self):
        self.penItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.penItem.pi))


class CommandQMark(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, pt):
        super(CommandQMark, self).__init__()
        self.scene = scene
        self.pt = pt
        self.qm = QMarkItemObject(self.pt)
        self.setText("QMark")

    def redo(self):
        self.qm.flash_redo()
        self.scene.addItem(self.qm.qmi)

    def undo(self):
        self.qm.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.qm.qmi))


class CommandText(QUndoCommand):
    # Very similar to CommandArrow, except that creates a textitem
    # rather than a graphicsitem
    def __init__(self, scene, blurb, ink):
        super(CommandText, self).__init__()
        self.scene = scene
        self.blurb = blurb
        self.setText("Text")

    def redo(self):
        self.blurb.flash_redo()
        self.scene.addItem(self.blurb)

    def undo(self):
        self.blurb.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.blurb))


class CommandTick(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, pt):
        super(CommandTick, self).__init__()
        self.scene = scene
        self.pt = pt
        self.tickItem = TickItemObject(self.pt)
        self.setText("Tick")

    def redo(self):
        self.tickItem.flash_redo()
        self.scene.addItem(self.tickItem.ti)

    def undo(self):
        self.tickItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.tickItem.ti))


class CommandEllipse(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, rect):
        super(CommandEllipse, self).__init__()
        self.scene = scene
        self.rect = rect
        self.ellipseItem = EllipseItemObject(self.rect)
        self.setText("Ellipse")

    def redo(self):
        self.ellipseItem.flash_redo()
        self.scene.addItem(self.ellipseItem.ei)

    def undo(self):
        self.ellipseItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.ellipseItem.ei))


# ################################
# Graphics Items
# These are the underlying graphicsitems that get put in the
# graphicsscene. We don't use them directly because we want
# to animate their undo/redo - and that only works for
# grahicsobjects which handle the actual animation of
# properties like width and colour. Hence the extra layer
# of classes.
class ArrowItem(QGraphicsPathItem):
    def __init__(self, pti, ptf):
        """Creates an arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super(ArrowItem, self).__init__()
        self.pti = pti
        self.ptf = ptf
        # vector direction of line
        delta = ptf - pti
        # length of the line
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        # unit vector in direction of line.
        ndelta = delta / el
        # orthogonal unit vector to line.
        northog = QPointF(-ndelta.y(), ndelta.x())
        # base of arrowhead
        self.arBase = ptf - 8 * ndelta
        # point of arrowhead
        self.arTip = ptf + 4 * ndelta
        # left-barb of the arrowhead
        self.arLeft = self.arBase - 5 * northog - 2 * ndelta
        # right-barb of the arrowhead
        self.arRight = self.arBase + 5 * northog - 2 * ndelta
        self.path = QPainterPath()
        # put a small ball at start of arrow.
        self.path.addEllipse(self.pti.x() - 3, self.pti.y() - 3, 6, 6)
        # draw line from pti to ptf
        self.path.moveTo(self.pti)
        self.path.lineTo(self.ptf)
        # line to left-barb then to base of arrowhead, then to right barb
        self.path.lineTo(self.arLeft)
        self.path.lineTo(self.arBase)
        self.path.lineTo(self.arRight)
        # then back to the end of the line.
        self.path.lineTo(self.ptf)
        self.setPath(self.path)
        # style the line.
        self.setPen(QPen(Qt.red, 2, cap=Qt.RoundCap, join=Qt.RoundJoin))
        # fill in the arrow with a red brush
        self.setBrush(QBrush(Qt.red))
        # The line is moveable and should signal any changes
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            # Push the command onto the stack.
            self.scene().undoStack.push(command)
        # Exec the parent class change command.
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Arrow",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]


class BoxItem(QGraphicsRectItem):
    # Very similar to the arrowitem but simpler to draw the box.
    def __init__(self, rect):
        super(BoxItem, self).__init__()
        self.rect = rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsRectItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Box",
            self.rect.left() + self.x(),
            self.rect.top() + self.y(),
            self.rect.width(),
            self.rect.height(),
        ]


class CrossItem(QGraphicsPathItem):
    # Very similar to the arrowitem.
    def __init__(self, pt):
        super(CrossItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        # Draw a cross whose vertex is at pt (under mouse click)
        self.path.moveTo(pt.x() - 12, pt.y() - 12)
        self.path.lineTo(pt.x() + 12, pt.y() + 12)
        self.path.moveTo(pt.x() - 12, pt.y() + 12)
        self.path.lineTo(pt.x() + 12, pt.y() - 12)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # self.dump()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return ["Cross", self.pt.x() + self.x(), self.pt.y() + self.y()]


class HighLightItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path):
        super(HighLightItem, self).__init__()
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(QColor(255, 255, 0, 64), 50))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # self.dump()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        pth = []
        for k in range(self.path.elementCount()):
            # e should be either a moveTo or a lineTo
            e = self.path.elementAt(k)
            if e.isMoveTo():
                pth.append(["m", e.x + self.x(), e.y + self.y()])
            else:
                if e.isLineTo():
                    pth.append(["l", e.x + self.x(), e.y + self.y()])
                else:
                    print("Problem pickling highlightitem path {}".format(self.path))
        return ["Highlight", pth]


class LineItem(QGraphicsLineItem):
    # Very similar to the arrowitem, but no arrowhead
    def __init__(self, pti, ptf):
        super(LineItem, self).__init__()
        self.pti = pti
        self.ptf = ptf
        self.setLine(QLineF(self.pti, self.ptf))
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsLineItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Line",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]


class PenItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path):
        super(PenItem, self).__init__()
        self.pi = QGraphicsPathItem()
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        pth = []
        for k in range(self.path.elementCount()):
            # e should be either a moveTo or a lineTo
            e = self.path.elementAt(k)
            if e.isMoveTo():
                pth.append(["m", e.x + self.x(), e.y + self.y()])
            else:
                if e.isLineTo():
                    pth.append(["l", e.x + self.x(), e.y + self.y()])
                else:
                    print("Problem pickling penitem path {}".format(self.path))
        return ["Pen", pth]


class QMarkItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but careful drawing the "?"
    def __init__(self, pt):
        super(QMarkItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        # Draw a ?-mark with barycentre under mouseclick
        self.path.moveTo(pt.x() - 6, pt.y() - 10)
        self.path.quadTo(pt.x() - 6, pt.y() - 15, pt.x(), pt.y() - 15)
        self.path.quadTo(pt.x() + 6, pt.y() - 15, pt.x() + 6, pt.y() - 10)
        self.path.cubicTo(
            pt.x() + 6, pt.y() - 1, pt.x(), pt.y() - 7, pt.x(), pt.y() + 2
        )
        self.path.moveTo(pt.x(), pt.y() + 12)
        self.path.lineTo(pt.x(), pt.y() + 10)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return ["QMark", self.pt.x() + self.x(), self.pt.y() + self.y()]


class TickItem(QGraphicsPathItem):
    # Very similar to the arrowitem
    def __init__(self, pt):
        super(TickItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        # Draw the checkmark with barycentre under mouseclick.
        self.path.moveTo(pt.x() - 10, pt.y())
        self.path.lineTo(pt.x(), pt.y() + 10)
        self.path.lineTo(pt.x() + 20, pt.y() - 10)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return ["Tick", self.pt.x() + self.x(), self.pt.y() + self.y()]


class EllipseItem(QGraphicsEllipseItem):
    # Very similar to the arrowitem
    def __init__(self, rect):
        super(EllipseItem, self).__init__()
        self.rect = rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsEllipseItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Ellipse",
            self.rect.left() + self.x(),
            self.rect.top() + self.y(),
            self.rect.width(),
            self.rect.height(),
        ]


class TextItem(QGraphicsTextItem):
    # Textitem is a qgraphicstextitem, has to handle
    # textinput and double-click to start editing etc.
    # Shift-return ends the editor
    def __init__(self, parent, fontsize=10):
        super(TextItem, self).__init__()
        self.parent = parent
        # Thick is thickness of bounding box hightlight used
        # to highlight the object when undo / redo happens.
        self.thick = 0
        self.setDefaultTextColor(Qt.red)
        self.setPlainText("")
        self.contents = ""
        self.font = QFont("Helvetica")
        self.font.setPointSizeF(min(24, fontsize * 2.5))
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

    def mouseDoubleClickEvent(self, event):
        # On double-click start the text-editor
        self.pngToText()
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()
        super(TextItem, self).mouseDoubleClickEvent(event)

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
        super(TextItem, self).focusOutEvent(event)

    def textToPng(self):
        self.contents = self.toPlainText()
        if self.contents[:4].upper() == "TEX:":
            texIt = self.contents[4:]
        else:
            texIt = self.contents

        if self.parent.latexAFragment(texIt):
            self.setPlainText("")
            tc = self.textCursor()
            qi = QImage("frag.png")
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
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # When redo-ing, draw a none->med->none border around text.
        self.anim.setDuration(250)
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


class DeltaItem(QGraphicsTextItem):
    # Similar to textitem above
    def __init__(self, pt, delta, fontsize=10):
        super(DeltaItem, self).__init__()
        self.thick = 2
        self.delta = delta
        self.setDefaultTextColor(Qt.red)
        # If positive mark then starts with a "+"-sign
        if self.delta > 0:
            self.setPlainText(" +{} ".format(self.delta))
        else:
            # else starts with a "-"-sign (unless zero).
            self.setPlainText(" {} ".format(self.delta))
        self.font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        self.font.setPointSize(min(30, fontsize * 3))
        self.setFont(self.font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # Has an animated border for undo/redo.
        self.anim = QPropertyAnimation(self, b"thickness")
        # centre under the mouse-click.
        cr = self.boundingRect()
        self.offset = QPointF(
            -(cr.right() + cr.left()) / 2, -(cr.top() + cr.bottom()) / 2
        )
        self.setPos(pt + self.offset)

    def paint(self, painter, option, widget):
        # paint the background
        painter.setPen(QPen(Qt.red, self.thick))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(DeltaItem, self).paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)

    def flash_undo(self):
        # Animate border when undo thin->thick->none
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # Animate border when undo thin->med->thin
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    def pickle(self):
        return [
            "Delta",
            self.delta,
            self.scenePos().x() - self.offset.x(),
            self.scenePos().y() - self.offset.y(),
        ]

    # For the animation of border
    @pyqtProperty(int)
    def thickness(self):
        return self.thick

    # For the animation of border
    @thickness.setter
    def thickness(self, value):
        self.thick = value
        self.update()


# ################################
# GraphicsItemObjects
# These are intermediate graphics objects that we need to
# to animate the undo/redo. These handle the animation of
# object properties like thickness or colour.
# Textitems (thankfully) handle animation themselves so we
# don't have to define objects for them.


class ArrowItemObject(QGraphicsObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf):
        super(ArrowItemObject, self).__init__()
        self.ai = ArrowItem(pti, ptf)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        # thin -> thick -> none.
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # thin -> med -> thin.
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    # Set and get thickness of the pen to draw the arrow.
    @pyqtProperty(int)
    def thickness(self):
        return self.ai.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ai.setPen(QPen(Qt.red, value))


class BoxItemObject(QGraphicsObject):
    # As per the ArrowItemObject, except animate the opacity of the box.
    def __init__(self, rect):
        super(BoxItemObject, self).__init__()
        self.bi = BoxItem(rect)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        # translucent -> opaque -> clear.
        self.anim.setDuration(500)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # translucent -> opaque -> translucent.
        self.anim.setDuration(250)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 64)
        self.anim.setEndValue(16)
        self.anim.start()

    @pyqtProperty(int)
    def opacity(self):
        return self.bi.brush().color().alpha()

    @opacity.setter
    def opacity(self, value):
        self.bi.setBrush(QBrush(QColor(255, 255, 0, value)))


class CrossItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(CrossItemObject, self).__init__()
        self.ci = CrossItem(pt)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.ci.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ci.setPen(QPen(Qt.red, value))


class HighLightItemObject(QGraphicsObject):
    # As per the ArrowItemObject except animate the opacity of
    # the highlighter path
    def __init__(self, path):
        super(HighLightItemObject, self).__init__()
        self.hli = HighLightItem(path)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 96)
        self.anim.setEndValue(64)
        self.anim.start()

    @pyqtProperty(int)
    def opacity(self):
        return self.hli.pen().color().alpha()

    @opacity.setter
    def opacity(self, value):
        self.hli.setPen(QPen(QColor(255, 255, 0, value), 50))


class LineItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pti, ptf):
        super(LineItemObject, self).__init__()
        self.li = LineItem(pti, ptf)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.li.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.li.setPen(QPen(Qt.red, value))


class PenItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, path):
        super(PenItemObject, self).__init__()
        self.pi = PenItem(path)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.pi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.pi.setPen(QPen(Qt.red, value))


class QMarkItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(QMarkItemObject, self).__init__()
        self.qmi = QMarkItem(pt)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.qmi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.qmi.setPen(QPen(Qt.red, value))


class TickItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(TickItemObject, self).__init__()
        self.ti = TickItem(pt)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.ti.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ti.setPen(QPen(Qt.red, value))


class WhiteBoxItemObject(QGraphicsObject):
    # As per the ArrowItemObject - animate thickness of boundary
    def __init__(self, rect):
        super(WhiteBoxItemObject, self).__init__()
        self.wbi = WhiteBoxItem(rect)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.wbi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.wbi.setPen(QPen(Qt.red, value))


class EllipseItemObject(QGraphicsObject):
    # As per the ArrowItemObject - animate thickness of boundary
    def __init__(self, rect):
        super(EllipseItemObject, self).__init__()
        self.ei = EllipseItem(rect)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.ei.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ei.setPen(QPen(Qt.red, value))


class CommandGDT(QUndoCommand):
    # GDT = group of delta and text
    # Command to do a delta and a textitem (ie a standard comment)
    # Must send a "the total mark has changed" signal
    def __init__(self, scene, pt, delta, blurb, fontsize):
        super(CommandGDT, self).__init__()
        self.scene = scene
        self.delta = delta
        self.blurb = blurb
        self.gdt = GroupDTItem(pt, self.delta, self.blurb, fontsize)
        self.setText("GroupDeltaText")

    def redo(self):
        self.gdt.di.flash_redo()
        self.gdt.blurb.flash_redo()
        self.scene.addItem(self.gdt)
        # Emit a markChangedSignal for the marker to pick up and change total.
        # Mark increased by delta
        self.scene.markChangedSignal.emit(self.delta)

    def undo(self):
        self.gdt.di.flash_undo()
        self.gdt.blurb.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.gdt))
        # Emit a markChangedSignal for the marker to pick up and change total.
        # Mark decreased by delta
        self.scene.markChangedSignal.emit(-self.delta)


class GroupDTItem(QGraphicsItemGroup):
    def __init__(self, pt, delta, blurb, fontsize):
        super(GroupDTItem, self).__init__()
        self.pt = pt
        self.di = DeltaItem(pt, delta, fontsize)  # positioned so centre under click
        self.blurb = blurb  # is a textitem already
        # move blurb so that its top-left corner is next to top-right corner of delta.
        cr = self.di.boundingRect()
        self.blurb.moveBy(
            (cr.right() + cr.left()) / 2 + 5, -(cr.top() + cr.bottom()) / 2
        )
        self.addToGroup(self.di)
        self.addToGroup(self.blurb)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsItemGroup.itemChange(self, change, value)

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        painter.setPen(QPen(Qt.red, 0.5))
        painter.setPen(Qt.DotLine)
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(GroupDTItem, self).paint(painter, option, widget)

    def pickle(self):
        return [
            "GroupDeltaText",
            self.pt.x() + self.x(),
            self.pt.y() + self.y(),
            self.di.delta,
            self.blurb.contents,
        ]
