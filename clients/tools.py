from math import sqrt

from PyQt5.QtCore import Qt, QLineF, QPointF,  pyqtProperty, QPropertyAnimation, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsObject, QGraphicsTextItem, QUndoCommand


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
        self.crossItem = CrossItemObject(self.pt)

    def redo(self):
        self.crossItem.flash_redo()
        self.scene.addItem(self.crossItem.ci)

    def undo(self):
        self.crossItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.crossItem.ci))


class CrossItemObject(QGraphicsObject):
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

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandTick(QUndoCommand):
    def __init__(self, scene, pt):
        super(CommandTick, self).__init__()
        self.scene = scene
        self.pt = pt
        self.tickItem = TickItemObject(self.pt)

    def redo(self):
        self.tickItem.flash_redo()
        self.scene.addItem(self.tickItem.ti)

    def undo(self):
        self.tickItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.tickItem.ti))


class TickItemObject(QGraphicsObject):
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


class TickItem(QGraphicsPathItem):
    def __init__(self, pt):
        super(TickItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        self.path.moveTo(pt.x()-10, pt.y())
        self.path.lineTo(pt.x(), pt.y()+10)
        self.path.lineTo(pt.x()+20, pt.y()-10)
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
        self.qm = QMarkItemObject(self.pt)

    def redo(self):
        self.qm.flash_redo()
        self.scene.addItem(self.qm.qmi)

    def undo(self):
        self.qm.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.qm.qmi))


class QMarkItemObject(QGraphicsObject):
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


class QMarkItem(QGraphicsPathItem):
    def __init__(self, pt):
        super(QMarkItem, self).__init__()
        self.pt = pt
        self.path = QPainterPath()
        self.path.moveTo(pt.x()-6, pt.y()-10)
        self.path.quadTo(pt.x()-6, pt.y()-15, pt.x(), pt.y()-15)
        self.path.quadTo(pt.x()+6, pt.y()-15, pt.x()+6, pt.y()-10)
        self.path.cubicTo(pt.x()+6, pt.y()-1, pt.x(), pt.y()-7, pt.x(), pt.y()+2)

        self.path.moveTo(pt.x(), pt.y()+12)
        self.path.lineTo(pt.x(), pt.y()+10)

        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandLine(QUndoCommand):
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        self.lineItem = LineItemObject(self.pti, self.ptf)

    def redo(self):
        self.lineItem.flash_redo()
        self.scene.addItem(self.lineItem.li)

    def undo(self):
        self.lineItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.lineItem.li))


class LineItemObject(QGraphicsObject):
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


class LineItem(QGraphicsLineItem):
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


class CommandArrow(QUndoCommand):
    def __init__(self, scene, pti, ptf):
        super(CommandArrow, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        self.arrowItem = ArrowItemObject(self.pti, self.ptf)

    def redo(self):
        self.arrowItem.flash_redo()
        self.scene.addItem(self.arrowItem.ai)

    def undo(self):
        self.arrowItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.arrowItem.ai))


class ArrowItemObject(QGraphicsObject):
    def __init__(self, pti, ptf):
        super(ArrowItemObject, self).__init__()
        self.ai = ArrowItem(pti, ptf)
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
        return self.ai.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ai.setPen(QPen(Qt.red, value))


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

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandPen(QUndoCommand):
    def __init__(self, scene, path):
        super(CommandPen, self).__init__()
        self.scene = scene
        self.path = path
        self.penItem = PenItemObject(self.path)

    def redo(self):
        self.penItem.flash_redo()
        self.scene.addItem(self.penItem.pi)

    def undo(self):
        self.penItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.penItem.pi))


class PenItemObject(QGraphicsObject):
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


class PenItem(QGraphicsPathItem):
    def __init__(self, path):
        super(PenItem, self).__init__()
        self.pi = QGraphicsPathItem()
        self.path = path
        self.setPath(self. path)
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandHighlight(QUndoCommand):
    def __init__(self, scene, path):
        super(CommandHighlight, self).__init__()
        self.scene = scene
        self.path = path
        self.highLightItem = HighLightItemObject(self.path)

    def redo(self):
        self.highLightItem.flash_redo()
        self.scene.addItem(self.highLightItem.hli)

    def undo(self):
        self.highLightItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.highLightItem.hli))


class HighLightItemObject(QGraphicsObject):
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


class HighLightItem(QGraphicsPathItem):
    def __init__(self, path):
        super(HighLightItem, self).__init__()
        self.path = path
        self.setPath(self.path)
        self.setPen(QPen(QColor(255, 255, 0, 64), 50))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)


class CommandBox(QUndoCommand):
    def __init__(self, scene, rect):
        super(CommandBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.boxItem = BoxItemObject(self.rect)

    def redo(self):
        self.boxItem.flash_redo()
        self.scene.addItem(self.boxItem.bi)

    def undo(self):
        self.boxItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.boxItem.bi))


class BoxItemObject(QGraphicsObject):
    def __init__(self, rect):
        super(BoxItemObject, self).__init__()
        self.bi = BoxItem(rect)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        self.anim.setDuration(500)
        self.anim.setStartValue(16)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
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


class BoxItem(QGraphicsRectItem):
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


class CommandWhiteBox(QUndoCommand):
    def __init__(self, scene, rect):
        super(CommandWhiteBox, self).__init__()
        self.scene = scene
        self.rect = rect
        self.whiteBoxItem = WhiteBoxItemObject(self.rect)

    def redo(self):
        self.whiteBoxItem.flash_redo()
        self.scene.addItem(self.whiteBoxItem.wbi)

    def undo(self):
        self.whiteBoxItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.whiteBoxItem.wbi))


class WhiteBoxItemObject(QGraphicsObject):
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


class WhiteBoxItem(QGraphicsRectItem):
    def __init__(self, rect):
        super(WhiteBoxItem, self).__init__()
        self.rect = rect
        self.setRect(self.rect)
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
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
        self.blurb.flash_redo()
        self.scene.addItem(self.blurb)

    def undo(self):
        self.blurb.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.blurb))


class TextItem(QGraphicsTextItem):
    def __init__(self, parent):
        super(TextItem, self).__init__()
        self.thick = 0
        self.setDefaultTextColor(Qt.red)
        self.setPlainText("")
        self.font = QFont("Helvetica")
        self.font.setPointSize(24)
        self.setFont(self.font)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.anim = QPropertyAnimation(self, b"thickness")

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

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ShiftModifier and event.key() == Qt.Key_Return:
            tc = self.textCursor()
            tc.clearSelection()
            self.setTextCursor(tc)
            self.setTextInteractionFlags(Qt.NoTextInteraction)
        super(TextItem, self).keyPressEvent(event)

    def paint(self, painter, option, widget):
        # paint the background
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
        self.anim.setDuration(500)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(250)
        self.anim.setStartValue(0)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(0)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.thick

    @thickness.setter
    def thickness(self, value):
        self.thick = value
        self.update()


class CommandDelta(QUndoCommand):
    def __init__(self, scene, pt, delta):
        super(CommandDelta, self).__init__()
        self.scene = scene
        self.delta = delta
        self.delItem = DeltaItem(pt, self.delta)

    def redo(self):
        self.delItem.flash_redo()
        self.scene.addItem(self.delItem)
        self.scene.markChangedSignal.emit(self.delta)

    def undo(self):
        self.delItem.flash_undo()
        QTimer.singleShot(500, lambda: self.scene.removeItem(self.delItem))
        self.scene.markChangedSignal.emit(-self.delta)


class DeltaItem(QGraphicsTextItem):
    def __init__(self, pt, delta):
        super(DeltaItem, self).__init__()
        self.thick = 2
        self.delta = delta
        self.setDefaultTextColor(Qt.red)
        if self.delta > 0:
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
        self.anim = QPropertyAnimation(self, b"thickness")
        cr = self.boundingRect()
        self.moveBy(-(cr.right()+cr.left())/2, -(cr.top()+cr.bottom())/2)

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
        self.anim.setDuration(500)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
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
        return self.thick

    @thickness.setter
    def thickness(self, value):
        self.thick = value
        self.update()
