import sys
import os

from PyQt5.QtCore import Qt, QLineF, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsRectItem, QGraphicsScene, QUndoStack

from tools import CommandArrow, CommandBox, CommandCross, CommandDelete, CommandDelta, CommandLine, CommandMoveItem, CommandMoveText, CommandPen, CommandText, CommandTick, TextItem

class PageScene(QGraphicsScene):
    markChangedSignal = pyqtSignal(int)
    def __init__(self, parent, imgName):
        super(PageScene, self).__init__(parent)
        self.imageName = imgName
        self.image = QPixmap(imgName)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)

        self.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.addItem(self.imageItem)
        self.undoStack = QUndoStack()

        self.mode = "pen"
        self.ink = QPen(Qt.red, 2)
        self.brush = QBrush(self.ink.color())
        self.lightBrush = QBrush(QColor(255, 255, 0, 16))
        self.textLock = False
        self.arrowFlag = 0

        self.zoomInk = QPen(Qt.green, 2)
        self.zoomBrush = QBrush(QColor(0, 255, 0, 16))

        self.originPos = QPointF(0, 0)
        self.currentPos = QPointF(0, 0)
        self.lastPos = QPointF(0, 0)
        self.path = QPainterPath()
        self.pathItem = QGraphicsPathItem()
        self.boxItem = QGraphicsRectItem()
        self.lineItem = QGraphicsLineItem()
        self.blurb = TextItem(self)
        self.deleteItem = None
        self.markDelta = 0
        self.commentText = ""

    def save(self):
        w = self.image.width()
        h = self.image.height()
        oimg = QPixmap(w, h)
        exporter = QPainter(oimg)
        self.render(exporter)
        exporter.end()
        oimg.save(self.imageName)

    def keyReleaseEvent(self,event):
        if event.key() == Qt.Key_Escape:
            self.clearFocus()
        else:
            super(PageScene, self).keyPressEvent(event)

    def mousePressEvent(self, event):
        fn = getattr(self, "%s_mousePressEvent"%self.mode, None)
        if fn:
            return fn(event)
        else:
            super(PageScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        fn = getattr(self, "%s_mouseMoveEvent"%self.mode, None)
        if fn:
            return fn(event)
        else:
            super(PageScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        fn = getattr(self, "%s_mouseReleaseEvent"%self.mode, None)
        if fn:
            return fn(event)
        else:
            super(PageScene, self).mouseReleaseEvent(event)

    def cross_mousePressEvent(self, event):
        pt = event.scenePos()
        if event.button() == Qt.LeftButton:
            command = CommandCross(self, pt)
        else:
            command = CommandTick(self, pt)
        self.undoStack.push(command)

    def tick_mousePressEvent(self, event):
        pt = event.scenePos()
        if event.button() == Qt.LeftButton:
            command = CommandTick(self, pt)
        else:
            command = CommandCross(self, pt)
        self.undoStack.push(command)

    def comment_mousePressEvent(self, event):
        self.originPos = event.scenePos() + QPointF(0, -24)
        self.blurb = TextItem(self)
        self.blurb.setPos(self.originPos)
        self.blurb.setPlainText(self.commentText)

        command = CommandText(self, self.blurb, self.ink)
        self.undoStack.push(command)

    def text_mousePressEvent(self, event):
        under = self.itemAt(event.scenePos(), QTransform())
        if isinstance(under, TextItem) and self.mode != 'move':
            under.setTextInteractionFlags(Qt.TextEditorInteraction)
            self.setFocusItem(under, Qt.MouseFocusReason)
            return

        self.originPos = event.scenePos() + QPointF(0, -12)
        self.blurb = TextItem(self)
        self.blurb.setPos(self.originPos)
        self.blurb.setFocus()
        command = CommandText(self, self.blurb, self.ink)
        self.undoStack.push(command)

    def line_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.arrowFlag = 0
        else:
            self.arrowFlag = 1

        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.lineItem = QGraphicsLineItem(QLineF(self.originPos, self.currentPos))
        self.lineItem.setPen(self.ink)
        self.addItem(self.lineItem)

    def line_mouseMoveEvent(self, event):
        self.currentPos = event.scenePos()
        self.lineItem.setLine(QLineF(self.originPos, self.currentPos))

    def line_mouseReleaseEvent(self, event):
        print("Line release ", type(self.lineItem))
        self.removeItem(self.lineItem)
        if self.arrowFlag == 0:
            command = CommandLine(self, self.originPos, self.currentPos)
        else:
            command = CommandArrow(self, self.originPos, self.currentPos)
        self.undoStack.push(command)

    def box_mousePressEvent(self, event):
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.boxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        self.boxItem.setPen(self.ink)
        self.boxItem.setBrush(self.lightBrush)
        self.addItem(self.boxItem)

    def box_mouseMoveEvent(self, event):
        self.currentPos = event.scenePos()
        if self.boxItem is None:
            self.boxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        else:
            self.boxItem.setRect(QRectF(self.originPos, self.currentPos))

    def box_mouseReleaseEvent(self, event):
        print("Box release ", type(self.boxItem))
        self.removeItem(self.boxItem)
        command = CommandBox(self, QRectF(self.originPos, self.currentPos))
        self.undoStack.push(command)

    def pen_mousePressEvent(self, event):
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.path = QPainterPath()
        self.path.moveTo(self.originPos)
        self.path.lineTo(self.currentPos)
        self.pathItem = QGraphicsPathItem(self.path)
        self.pathItem.setPen(self.ink)
        self.addItem(self.pathItem)

    def pen_mouseMoveEvent(self, event):
        self.currentPos = event.scenePos()
        self.path.lineTo(self.currentPos)
        self.pathItem.setPath(self.path)

    def pen_mouseReleaseEvent(self, event):
        print("Pen release ", type(self.pathItem))
        self.removeItem(self.pathItem)
        command = CommandPen(self, self.path)
        self.undoStack.push(command)

    def delete_mousePressEvent(self,event):
        self.originPos = event.scenePos()
        self.deleteItem = self.itemAt(self.originPos, QTransform())
        if self.deleteItem == self.imageItem:
            self.deleteItem = None
            return

        command = CommandDelete(self, self.deleteItem)
        self.undoStack.push(command)

    def move_mousePressEvent(self,event):
        self.parent().setCursor(Qt.ClosedHandCursor)
        super(PageScene, self).mousePressEvent(event)

    def move_mouseReleaseEvent(self,event):
        self.parent().setCursor(Qt.OpenHandCursor)
        super(PageScene, self).mouseReleaseEvent(event)


    def pan_mousePressEvent(self, event):
        pass

    def pan_mouseMoveEvent(self, event):
        pass

    def pan_mouseReleaseEvent(self, event):
        pass

    def zoom_mousePressEvent(self, event):
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.boxItem = QGraphicsRectItem(QRectF(self.originPos, self.currentPos))
        self.boxItem.setPen(self.zoomInk)
        self.boxItem.setBrush(self.zoomBrush)
        self.addItem(self.boxItem)

    def zoom_mouseMoveEvent(self, event):
        self.currentPos = event.scenePos()
        self.boxItem.setRect(QRectF(self.originPos, self.currentPos))

    def zoom_mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.parent().scale(0.8, 0.8)
        else:
            rec = self.boxItem.rect()
            if rec.height() >= 100 and rec.width() >= 100:
                self.parent().fitInView(self.boxItem, Qt.KeepAspectRatio)
        print("Zoom release ", type(self.boxItem))
        self.removeItem(self.boxItem)

    def delta_mousePressEvent(self, event):
        pt = event.scenePos()
        command = CommandDelta(self, pt, self.markDelta)
        self.undoStack.push(command)
