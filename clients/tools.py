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

## move and delete commands
class CommandDelete(QUndoCommand):
    # Deletes the graphicsitem. Have to be careful when it is
    # a delta-item which changes the current mark
    def __init__(self, scene, deleteItem):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem
        self.setText("Delete")

    def redo(self):
        # check to see if mid-delete
        if self.deleteItem.animateFlag:
            return  # this avoids user deleting same object mid-delete animation.

        # If the object is a DeltaItem then change mark
        if isinstance(self.deleteItem, DeltaItem):
            # Mark decreases by delta - since deleting, this is like an "undo"
            self.scene.changeTheMark(self.deleteItem.delta, undo=True)
        if isinstance(self.deleteItem, GroupDTItem):
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=True)
        # nicely animate the deletion - since deleting, this is like an "undo"
        self.deleteItem.animateFlag = True
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_undo()
            QTimer.singleShot(200, lambda: self.scene.removeItem(self.deleteItem))
        else:
            self.scene.removeItem(self.deleteItem)

    def undo(self):
        # If the object is a DeltaItem then change mark.
        if isinstance(self.deleteItem, DeltaItem):
            # Mark increases by delta  - since deleting, this is like an "redo"
            self.scene.changeTheMark(self.deleteItem.delta, undo=False)
        # If the object is a GroupTextDeltaItem then change mark
        if isinstance(self.deleteItem, GroupDTItem):
            # Mark decreases by delta -  - since deleting, this is like an "redo"
            self.scene.changeTheMark(self.deleteItem.di.delta, undo=False)
        # nicely animate the undo of deletion
        self.deleteItem.animateFlag = False
        self.scene.addItem(self.deleteItem)
        if self.deleteItem.animator is not None:
            for X in self.deleteItem.animator:
                X.flash_redo()


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


# Arrow stuff
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.arrowItem.ai))


class ArrowItemObject(QGraphicsObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf):
        super(ArrowItemObject, self).__init__()
        self.ai = ArrowItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        # thin -> thick -> none.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # thin -> med -> thin.
        self.anim.setDuration(200)
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


class ArrowItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, parent=None):
        """Creates an arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super(ArrowItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
        self.ptf = ptf
        self.pti = pti
        # vector direction of line
        delta = ptf - pti
        # length of the line
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        # unit vector in direction of line.
        ndelta = delta / el
        # orthogonal unit vector to line.
        northog = QPointF(-ndelta.y(), ndelta.x())
        # base of arrowhead
        self.arBase = ptf - 16 * ndelta
        # point of arrowhead
        self.arTip = ptf + 8 * ndelta
        # left-barb of the arrowhead
        self.arLeft = self.arBase - 10 * northog - 4 * ndelta
        # right-barb of the arrowhead
        self.arRight = self.arBase + 10 * northog - 4 * ndelta
        self.path = QPainterPath()
        # put a small ball at start of arrow.
        self.path.addEllipse(self.pti.x() - 6, self.pti.y() - 6, 12, 12)
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(ArrowItem, self).paint(painter, option, widget)


# Double Arrow stuff
class CommandArrowDouble(QUndoCommand):
    # Command to create/remove an arrow object
    def __init__(self, scene, pti, ptf):
        super(CommandArrowDouble, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        # create an arrow item
        self.arrowItem = ArrowDoubleItemObject(self.pti, self.ptf)
        self.setText("ArrowDouble")

    def redo(self):
        # arrow item knows how to highlight on undo and redo.
        self.arrowItem.flash_redo()
        self.scene.addItem(self.arrowItem.ai)

    def undo(self):
        # the undo animation takes 0.5s
        # so trigger its removal after 0.5s.
        self.arrowItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.arrowItem.ai))


class ArrowDoubleItemObject(QGraphicsObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf):
        super(ArrowDoubleItemObject, self).__init__()
        self.ai = ArrowDoubleItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        # thin -> thick -> none.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # thin -> med -> thin.
        self.anim.setDuration(200)
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


class ArrowDoubleItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, parent=None):
        """Creates an double-headed arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super(ArrowDoubleItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
        self.ptf = ptf
        self.pti = pti
        self.path = QPainterPath()
        # Some vectors:
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        # build arrow
        arBase = pti + 16 * ndelta
        arTip = pti - 8 * ndelta
        arLeft = arBase + 10 * northog + 4 * ndelta
        arRight = arBase - 10 * northog + 4 * ndelta
        # draw first arrow.
        self.path.moveTo(self.pti)
        self.path.lineTo(arLeft)
        self.path.lineTo(arBase)
        self.path.lineTo(arRight)
        self.path.lineTo(self.pti)
        # draw line from pti to ptf
        self.path.lineTo(self.ptf)
        # other arrowhead
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        # line to left-barb then to base of arrowhead, then to right barb
        self.path.lineTo(arLeft)
        self.path.lineTo(arBase)
        self.path.lineTo(arRight)
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
            "ArrowDouble",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(ArrowDoubleItem, self).paint(painter, option, widget)


# Box stuff
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.boxItem.bi))


class BoxItemObject(QGraphicsObject):
    # As per the ArrowItemObject, except animate the opacity of the box.
    def __init__(self, rect):
        super(BoxItemObject, self).__init__()
        self.bi = BoxItem(rect, self)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        # translucent -> opaque -> clear.
        self.anim.setDuration(200)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # translucent -> opaque -> translucent.
        self.anim.setDuration(200)
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


class BoxItem(QGraphicsRectItem):
    # Very similar to the arrowitem but simpler to draw the box.
    def __init__(self, rect, parent=None):
        super(BoxItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(BoxItem, self).paint(painter, option, widget)


# cross stuff
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.crossItem.ci))


class CrossItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(CrossItemObject, self).__init__()
        self.ci = CrossItem(pt, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class CrossItem(QGraphicsPathItem):
    # Very similar to the arrowitem.
    def __init__(self, pt, parent=None):
        super(CrossItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
            # paint the normal item with the default 'paint' method
        super(CrossItem, self).paint(painter, option, widget)


# Delta stuff
class CommandDelta(QUndoCommand):
    # Very similar to CommandArrow
    # But must send new mark to scene
    def __init__(self, scene, pt, delta, fontsize):
        super(CommandDelta, self).__init__()
        self.scene = scene
        self.pt = pt
        self.delta = delta
        self.delItem = DeltaItem(self.pt, self.delta, fontsize)
        self.setText("Delta")

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.delta, undo=False)
        self.delItem.flash_redo()
        self.scene.addItem(self.delItem)

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.delta, undo=True)
        self.delItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.delItem))


class DeltaItem(QGraphicsTextItem):
    # Similar to textitem
    def __init__(self, pt, delta, fontsize=10):
        super(DeltaItem, self).__init__()
        self.animator = [self]
        self.animateFlag = False
        self.thick = 2
        self.delta = delta
        self.setDefaultTextColor(Qt.red)
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
        self.setPos(pt)
        cr = self.boundingRect()
        self.offset = -cr.height() / 2
        self.moveBy(0, self.offset)

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            if self.group() is None:
                painter.setPen(QPen(QColor(255, 165, 0), 4))
                painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
                painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
                painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
                painter.drawRoundedRect(option.rect, 10, 10)
        else:
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
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # Animate border when undo thin->med->thin
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    def pickle(self):
        return [
            "Delta",
            self.delta,
            self.scenePos().x(),
            self.scenePos().y() - self.offset,
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


# Ellipse
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.ellipseItem.ei))


class EllipseItemObject(QGraphicsObject):
    # As per the ArrowItemObject - animate thickness of boundary
    def __init__(self, rect):
        super(EllipseItemObject, self).__init__()
        self.ei = EllipseItem(rect, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class EllipseItem(QGraphicsEllipseItem):
    # Very similar to the arrowitem
    def __init__(self, rect, parent=None):
        super(EllipseItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(EllipseItem, self).paint(painter, option, widget)


# Highlight
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.highLightItem.hli))


class HighLightItemObject(QGraphicsObject):
    # As per the ArrowItemObject except animate the opacity of
    # the highlighter path
    def __init__(self, path):
        super(HighLightItemObject, self).__init__()
        self.hli = HighLightItem(path, self)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class HighLightItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path, parent=None):
        super(HighLightItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(HighLightItem, self).paint(painter, option, widget)


# Line
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.lineItem.li))


class LineItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pti, ptf):
        super(LineItemObject, self).__init__()
        self.li = LineItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class LineItem(QGraphicsLineItem):
    # Very similar to the arrowitem, but no arrowhead
    def __init__(self, pti, ptf, parent=None):
        super(LineItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        super(LineItem, self).paint(painter, option, widget)


# Pen
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.penItem.pi))


class PenItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, path):
        super(PenItemObject, self).__init__()
        self.pi = PenItem(path, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class PenItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but much simpler
    def __init__(self, path, parent=None):
        super(PenItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(PenItem, self).paint(painter, option, widget)


# Pen-with-arrows
class CommandPenArrow(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandPenArrow, self).__init__()
        self.scene = scene
        self.path = path
        self.penItem = PenArrowItemObject(self.path)
        self.setText("PenArrow")

    def redo(self):
        self.penItem.flash_redo()
        self.scene.addItem(self.penItem.pi)

    def undo(self):
        self.penItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.penItem.pi))


class PenArrowItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, path):
        super(PenArrowItemObject, self).__init__()
        self.pi = PenArrowItem(path, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.pi.pi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.pi.pi.setPen(QPen(Qt.red, value))
        self.pi.endi.setPen(QPen(Qt.red, value))
        self.pi.endf.setPen(QPen(Qt.red, value))


class PenArrowItem(QGraphicsItemGroup):
    def __init__(self, path, parent=None):
        super(PenArrowItem, self).__init__()
        self.pi = QGraphicsPathItem()
        self.path = path
        self.animator = [parent]
        self.animateFlag = False

        # set arrowhead initial
        e0 = self.path.elementAt(0)
        e1 = self.path.elementAt(1)
        pti = QPointF(e1.x, e1.y)
        ptf = QPointF(e0.x, e0.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.ari = QPainterPath()
        self.ari.moveTo(ptf)
        self.ari.lineTo(arLeft)
        self.ari.lineTo(arBase)
        self.ari.lineTo(arRight)
        self.ari.lineTo(ptf)
        self.endi = QGraphicsPathItem()
        self.endi.setPath(self.ari)
        # set arrowhead final
        e2 = self.path.elementAt(self.path.elementCount() - 2)
        e3 = self.path.elementAt(self.path.elementCount() - 1)
        pti = QPointF(e2.x, e2.y)
        ptf = QPointF(e3.x, e3.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.arf = QPainterPath()
        self.arf.moveTo(ptf)
        self.arf.lineTo(arLeft)
        self.arf.lineTo(arBase)
        self.arf.lineTo(arRight)
        self.arf.lineTo(ptf)
        self.endf = QGraphicsPathItem()
        self.endf.setPath(self.arf)
        # put everything together
        self.pi.setPath(self.path)
        self.pi.setPen(QPen(Qt.red, 2))
        self.endi.setPen(QPen(Qt.red, 2))
        self.endi.setBrush(QBrush(Qt.red))
        self.endf.setPen(QPen(Qt.red, 2))
        self.endf.setBrush(QBrush(Qt.red))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.addToGroup(self.pi)
        self.addToGroup(self.endi)
        self.addToGroup(self.endf)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsItemGroup.itemChange(self, change, value)

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
                    print("Problem pickling penarrowitem path {}".format(self.path))
        return ["PenArrow", pth]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(PenArrowItem, self).paint(painter, option, widget)


# Question-mark
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.qm.qmi))


class QMarkItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(QMarkItemObject, self).__init__()
        self.qmi = QMarkItem(pt, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class QMarkItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but careful drawing the "?"
    def __init__(self, pt, parent=None):
        super(QMarkItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(QMarkItem, self).paint(painter, option, widget)


# tick-mark
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
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.tickItem.ti))


class TickItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(TickItemObject, self).__init__()
        self.ti = TickItem(pt, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
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


class TickItem(QGraphicsPathItem):
    # Very similar to the arrowitem
    def __init__(self, pt, parent=None):
        super(TickItem, self).__init__()
        self.animator = [parent]
        self.animateFlag = False
        self.pt = pt
        self.path = QPainterPath()
        # Draw the checkmark with barycentre under mouseclick.
        self.path.moveTo(pt.x() - 10, pt.y() - 10)
        self.path.lineTo(pt.x(), pt.y())
        self.path.lineTo(pt.x() + 20, pt.y() - 20)
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(TickItem, self).paint(painter, option, widget)


# Text
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
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
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


class CommandGDT(QUndoCommand):
    # GDT = group of delta and text
    # Command to do a delta and a textitem (ie a standard comment)
    # Must change mark
    def __init__(self, scene, pt, delta, blurb, fontsize):
        super(CommandGDT, self).__init__()
        self.scene = scene
        self.pt = pt
        self.delta = delta
        self.blurb = blurb
        self.gdt = GroupDTItem(self.pt, self.delta, self.blurb, fontsize)
        self.setText("GroupDeltaText")

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.delta, undo=False)
        self.scene.addItem(self.gdt)
        self.gdt.blurb.flash_redo()
        self.gdt.di.flash_redo()

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.delta, undo=True)
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.gdt))
        self.gdt.blurb.flash_undo()
        self.gdt.di.flash_undo()


class GroupDTItem(QGraphicsItemGroup):
    def __init__(self, pt, delta, blurb, fontsize):
        super(GroupDTItem, self).__init__()
        self.pt = pt
        self.di = DeltaItem(
            self.pt, delta, fontsize
        )  # positioned so centre under click
        self.blurb = blurb  # is a textitem already
        self.blurb.setTextInteractionFlags(Qt.NoTextInteraction)

        # check if needs tex->latex
        self.blurb.textToPng()

        # move blurb so that its top-left corner is next to top-right corner of delta.
        self.tweakPositions(delta)

        # set up animators for delete
        self.animator = [self.di, self.blurb]
        self.animateFlag = False
        self.thick = 1

        self.addToGroup(self.di)
        self.addToGroup(self.blurb)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def tweakPositions(self, dlt):
        pt = self.di.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        if dlt != ".":
            cr = self.di.boundingRect()
            self.blurb.moveBy(cr.width() + 5, 0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsItemGroup.itemChange(self, change, value)

    def pickle(self):
        return [
            "GroupDeltaText",
            self.pt.x() + self.x(),
            self.pt.y() + self.y(),
            self.di.delta,
            self.blurb.contents,
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().imageItem, mode=Qt.ContainsItemShape):
            painter.setPen(QPen(QColor(255, 165, 0), 4))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        else:
            # paint a bounding rectangle for undo/redo highlighting
            painter.setPen(QPen(QColor(255, 0, 0), self.thick, style=Qt.DotLine))
            painter.drawRoundedRect(option.rect, 10, 10)
            pass
        super(GroupDTItem, self).paint(painter, option, widget)


class GhostComment(QGraphicsItemGroup):
    def __init__(self, dlt, txt, fontsize):
        super(GhostComment, self).__init__()
        self.di = GhostDelta(dlt, fontsize)
        self.blurb = GhostText(txt, fontsize)
        self.changeComment(dlt, txt)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def tweakPositions(self, dlt, txt):
        pt = self.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        if dlt == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        else:
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            # check if blurb is empty, move accordingly to hide it
            if txt == "":
                self.blurb.moveBy(0, -cr.height() / 2)
            else:
                self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

    def changeComment(self, dlt, txt):
        # need to force a bounding-rect update by removing an item and adding it back
        self.removeFromGroup(self.di)
        self.removeFromGroup(self.blurb)
        # change things
        self.di.changeDelta(dlt)
        self.blurb.changeText(txt)
        # move to correct positions
        self.tweakPositions(dlt, txt)
        self.addToGroup(self.blurb)
        if dlt == ".":
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        painter.setPen(QPen(Qt.blue, 0.5, style=Qt.DotLine))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(GhostComment, self).paint(painter, option, widget)


class GhostDelta(QGraphicsTextItem):
    # Similar to textitem
    def __init__(self, delta, fontsize=10):
        super(GhostDelta, self).__init__()
        self.delta = int(delta)
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(" {} ".format(self.delta))
        self.font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        self.font.setPointSize(min(30, fontsize * 3))
        self.setFont(self.font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def changeDelta(self, dlt):
        self.delta = dlt
        self.setPlainText(" {} ".format(self.delta))

    def paint(self, painter, option, widget):
        # paint the background
        painter.setPen(QPen(Qt.blue, 1))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(GhostDelta, self).paint(painter, option, widget)


class GhostText(QGraphicsTextItem):
    # Textitem is a qgraphicstextitem, has to handle
    # textinput and double-click to start editing etc.
    # Shift-return ends the editor
    def __init__(self, txt, fontsize=10):
        super(GhostText, self).__init__()
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(txt)
        self.font = QFont("Helvetica")
        self.font.setPointSizeF(min(24, fontsize * 2.5))
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
            if self.scene().latexAFragment(texIt):
                self.setPlainText("")
                tc = self.textCursor()
                qi = QImage("frag.png")
                tc.insertImage(qi)
