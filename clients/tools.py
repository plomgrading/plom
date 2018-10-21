import sys
from math import sqrt

from PyQt5.QtCore import Qt, QLineF, QPointF
from PyQt5.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QTextCursor
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsTextItem, QUndoCommand

class CommandDelete(QUndoCommand):
    def __init__(self, scene, deleteItem):
        super(CommandDelete, self).__init__()
        self.scene = scene
        self.deleteItem = deleteItem

    def redo(self):
        if isinstance(self.deleteItem, DeltaItem):
            self.scene.markChangedSignal.emit(-self.deleteItem.delta)
        self.scene.removeItem(self.deleteItem)

    def undo(self):
        if isinstance(self.deleteItem, DeltaItem):
            self.scene.markChangedSignal.emit(self.deleteItem.delta)
        self.scene.addItem(self.deleteItem)

class CommandMoveItem(QUndoCommand):
    def __init__(self, xitem, delta):
        super(CommandMoveItem, self).__init__()
        self.xitem = xitem
        self.delta = delta

    def id(self):
        return 101

    def redo(self):
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        self.xitem.setPos(self.xitem.pos()+self.delta)
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def undo(self):
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        self.xitem.setPos(self.xitem.pos()-self.delta)
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def mergeWith(self, other):
        if self.xitem != other.xitem:
            return False
        self.delta = other.delta
        return True

class CommandMoveText(QUndoCommand):
    def __init__(self, xitem, new_pos):
        super(CommandMoveText, self).__init__()
        self.xitem = xitem
        self.old_pos = xitem.pos()
        self.new_pos = new_pos

    def id(self):
        return 102

    def redo(self):
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        self.xitem.setPos(self.new_pos)
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def undo(self):
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        self.xitem.setPos(self.old_pos)
        self.xitem.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def mergeWith(self, other):
        if self.xitem != other.xitem:
            return False
        self.new_pos = other.new_pos
        return True


class CommandCross(QUndoCommand):
    def __init__(self, scene, pt):
        super(CommandCross, self).__init__()
        self.scene = scene
        self.pt = pt
        self.pathItem = CrossItem(self.pt)

    def redo(self):
        self.scene.addItem(self.pathItem)

    def undo(self):
        self.scene.removeItem(self.pathItem)


class CrossItem(QGraphicsPathItem):
    def __init__(self, pt):
        super(CrossItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        self.path.moveTo(pt.x()-12, pt.y()-12)
        self.path.lineTo(pt.x()+12, pt.y()+12)
        self.path.moveTo(pt.x()-12, pt.y()+12)
        self.path.lineTo(pt.x()+12, pt.y()-12)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self,change,value)

class CommandTick(QUndoCommand):
    def __init__(self, scene, pt):
        super(CommandTick, self).__init__()
        self.scene = scene
        self.pt = pt
        self.pathItem = TickItem(self.pt)

    def redo(self):
        self.scene.addItem(self.pathItem)

    def undo(self):
        self.scene.removeItem(self.pathItem)

class TickItem(QGraphicsPathItem):
    def __init__(self, pt):
        super(TickItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        self.path.moveTo(pt.x()-10, pt.y()-10)
        self.path.lineTo(pt.x(), pt.y())
        self.path.lineTo(pt.x()+20, pt.y()-20)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandQMark(QUndoCommand):
    def __init__(self, scene, pt):
        super(CommandQMark, self).__init__()
        self.scene = scene
        self.pt = pt
        self.pathItem = QMarkItem(self.pt)

    def redo(self):
        self.scene.addItem(self.pathItem)

    def undo(self):
        self.scene.removeItem(self.pathItem)

class QMarkItem(QGraphicsTextItem):
    def __init__(self, pt):
        super(QMarkItem, self).__init__()
        self.setDefaultTextColor(Qt.red)
        self.setPlainText("?")
        self.font = QFont("Helvetica")
        self.font.setPointSize(30)
        self.setFont(self.font)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(pt.x()-15, pt.y()-50)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)





class CommandLine(QUndoCommand):
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        self.lineItem = LineItem(self.pti, self.ptf)

    def redo(self):
        self.scene.addItem(self.lineItem)

    def undo(self):
        self.scene.removeItem(self.lineItem)

class LineItem(QGraphicsLineItem):
    def __init__(self, pti, ptf):
        super(LineItem, self).__init__()
        self.pti = pti
        self.ptf = ptf
        self.setLine(QLineF(self.pti, self.ptf))
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsLineItem.itemChange(self, change, value)

class CommandArrow(QUndoCommand):
    def __init__(self, scene, pti, ptf):
        super(CommandArrow, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        self.arrowItem = ArrowItem(self.pti, self.ptf)

    def redo(self):
        self.scene.addItem(self.arrowItem)

    def undo(self):
        self.scene.removeItem(self.arrowItem)

class ArrowItem(QGraphicsPathItem):
    def __init__(self, pti, ptf):
        super(ArrowItem, self).__init__()
        self.pti = pti
        self.ptf = ptf
        delta = ptf-pti
        el = sqrt(delta.x()**2 + delta.y()**2)
        ndelta = delta/el
        northog = QPointF(-ndelta.y(), ndelta.x())
        self.arBase = ptf-8*ndelta
        self.arTip = ptf+4*ndelta
        self.arLeft = self.arBase-5*northog-2*ndelta
        self.arRight = self.arBase+5*northog-2*ndelta

        self.path = QPainterPath()
        self.path.addEllipse(self.pti.x()-3, self.pti.y()-3, 6, 6)
        self.path.moveTo(self.pti)
        self.path.lineTo(self.ptf)
        self.path.lineTo(self.arLeft)
        self.path.lineTo(self.arBase)
        self.path.lineTo(self.arRight)
        self.path.lineTo(self.ptf)

        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 2, cap=Qt.RoundCap, join=Qt.RoundJoin))
        self.setBrush(QBrush(Qt.red))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

class CommandPen(QUndoCommand):
    def __init__(self, scene, path):
        super(CommandPen, self).__init__()
        self.scene = scene
        self.path = path
        self.pathItem = PathItem(self.path)

    def redo(self):
        self.scene.addItem(self.pathItem)

    def undo(self):
        self.scene.removeItem(self.pathItem)

class PathItem(QGraphicsPathItem):
    def __init__(self, path):
        super(PathItem, self).__init__()
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

class CommandHighlight(QUndoCommand):
    def __init__(self, scene, path):
        super(CommandHighlight, self).__init__()
        self.scene = scene
        self.path = path
        self.pathItem = HighLightItem(self.path)

    def redo(self):
        self.scene.addItem(self.pathItem)

    def undo(self):
        self.scene.removeItem(self.pathItem)

class HighLightItem(QGraphicsPathItem):
    def __init__(self, path):
        super(HighLightItem, self).__init__()
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(QColor(255, 255, 0, 64), 50))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

class CommandBox(QUndoCommand):
    def __init__(self, scene, rect):
        super(CommandBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.boxItem = BoxItem(self.rect)

    def redo(self):
        self.scene.addItem(self.boxItem)

    def undo(self):
        self.scene.removeItem(self.boxItem)

class BoxItem(QGraphicsRectItem):
    def __init__(self, rect):
        super(BoxItem, self).__init__()
        self.rect=rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 0, 16)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsRectItem.itemChange(self, change, value)

class CommandWhiteBox(QUndoCommand):
    def __init__(self, scene, rect):
        super(CommandWhiteBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.whiteBoxItem = WhiteBoxItem(self.rect)

    def redo(self):
        self.scene.addItem(self.whiteBoxItem)

    def undo(self):
        self.scene.removeItem(self.whiteBoxItem)

class WhiteBoxItem(QGraphicsRectItem):
    def __init__(self, rect):
        super(WhiteBoxItem, self).__init__()
        self.rect=rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsRectItem.itemChange(self, change, value)


class CommandText(QUndoCommand):
    def __init__(self, scene, blurb, ink):
        super(CommandText, self).__init__()
        self.scene = scene
        self.blurb = blurb

    def redo(self):
        self.scene.addItem(self.blurb)

    def undo(self):
        self.scene.removeItem(self.blurb)

class TextItem(QGraphicsTextItem):
    def __init__(self, parent):
        super(TextItem, self).__init__()
        self.setDefaultTextColor(Qt.red)
        self.setPlainText("")
        self.font = QFont("Helvetica")
        self.font.setPointSize(24)
        self.setFont(self.font)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)

    def mouseDoubleClickEvent(self, event):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus()

    def focusInEvent(self, event):
        super(TextItem, self).focusInEvent(event)

    def focusOutEvent(self, event):
        tc = self.textCursor()
        tc.clearSelection()
        self.setTextCursor(tc)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        super(TextItem, self).focusOutEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsTextItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)  #Notice that the value here is the new position, not the delta.
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)

class CommandDelta(QUndoCommand):
    def __init__(self, scene, pt, delta):
        super(CommandDelta, self).__init__()
        self.scene = scene
        self.delta = delta
        self.delItem = DeltaItem(pt, self.delta)

    def redo(self):
        self.scene.addItem(self.delItem)
        self.scene.markChangedSignal.emit(self.delta)

    def undo(self):
        self.scene.removeItem(self.delItem)
        self.scene.markChangedSignal.emit(-self.delta)

class DeltaItem(QGraphicsTextItem):
    def __init__(self, pt, delta):
        super(DeltaItem, self).__init__()
        self.delta = delta
        self.setDefaultTextColor(Qt.red)
        if self.delta>0:
            self.setPlainText(" +{} ".format(self.delta))
        else:
            self.setPlainText(" {} ".format(self.delta))
        self.font = QFont("Helvetica")
        self.font.setPointSize(30)
        self.setFont(self.font)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(pt)

    def paint(self, painter, option, widget):
        # paint the background
        painter.setPen(QPen(Qt.red, 2))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(DeltaItem, self).paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)
