import sys
import os

from PyQt5.QtCore import Qt, QLineF, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap, QTransform, QFont
from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsRectItem, QGraphicsScene, QUndoStack, QGraphicsItemGroup, QGraphicsTextItem

from tools import CommandArrow, CommandBox, CommandCross, CommandDelete, CommandDelta, CommandHighlight, CommandLine, CommandMoveItem, CommandMoveText, CommandPen, CommandQMark, CommandText, CommandTick, TextItem, CommandWhiteBox

class ScoreBox(QGraphicsTextItem):
    def __init__(self):
        super(ScoreBox, self).__init__()
        self.score = 0
        self.maxScore = 0
        self.setDefaultTextColor(Qt.red)
        self.font = QFont("Helvetica")
        self.font.setPointSize(36)
        self.setFont(self.font)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setPos(4, 4)
        self.changeScore(0)

    def changeScore(self, x):
        self.score = x
        self.setPlainText("{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2)))

    def changeMax(self, x):
        self.maxScore = x
        self.setPlainText("{} out of {}".format(str(x).zfill(2), str(self.maxScore).zfill(2)))

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.drawRoundedRect(option.rect, 10, 10)
        super(ScoreBox, self).paint(painter, option, widget)

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
        self.highlight = QPen(QColor(255, 255, 0, 64), 50)
        self.brush = QBrush(self.ink.color())
        self.lightBrush = QBrush(QColor(255, 255, 0, 16))
        self.textLock = False
        self.arrowFlag = 0
        self.highlightFlag = 0
        self.whiteFlag = 0

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
        self.commentDelta = 0

        self.scoreBox = ScoreBox()
        self.scoreBox.setZValue(10)
        self.addItem(self.scoreBox)

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
        if event.button() == Qt.RightButton:
            command = CommandTick(self, pt)
        elif event.button() == Qt.MiddleButton:
            command = CommandQMark(self, pt)
        else:
            command = CommandCross(self, pt)
        self.undoStack.push(command)

    def tick_mousePressEvent(self, event):
        pt = event.scenePos()
        if event.button() == Qt.RightButton:
            command = CommandCross(self, pt)
        elif event.button() == Qt.MiddleButton:
            command = CommandQMark(self, pt)
        else:
            command = CommandTick(self, pt)
        self.undoStack.push(command)

    def comment_mousePressEvent(self, event):
        pt = event.scenePos()
        offset = QPointF(0,-24)
        if self.commentDelta != 0:  # then put down a marker. Else just the comment.
            command = CommandDelta(self, pt, self.commentDelta)
            self.undoStack.push(command)
            offset = QPointF(36,-24)

        self.originPos = event.scenePos() + offset
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
        # print("Line release ", type(self.lineItem))
        self.removeItem(self.lineItem)
        if self.arrowFlag == 0:
            command = CommandLine(self, self.originPos, self.currentPos)
        else:
            command = CommandArrow(self, self.originPos, self.currentPos)
        self.arrowFlag = 0
        self.undoStack.push(command)

    def box_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.whiteFlag = 0
        else:
            self.whiteFlag = 1

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
        self.removeItem(self.boxItem)
        if self.whiteFlag == 0:
            command = CommandBox(self, QRectF(self.originPos, self.currentPos))
        else:
            command = CommandWhiteBox(self, QRectF(self.originPos, self.currentPos))
        self.whiteFlag = 0
        self.undoStack.push(command)

    def pen_mousePressEvent(self, event):
        self.originPos = event.scenePos()
        self.currentPos = self.originPos
        self.path = QPainterPath()
        self.path.moveTo(self.originPos)
        self.path.lineTo(self.currentPos)
        self.pathItem = QGraphicsPathItem(self.path)

        if event.button() == Qt.LeftButton:
            self.pathItem.setPen(self.ink)
            self.highlightFlag = 0
        else:
            self.pathItem.setPen(self.highlight)
            self.highlightFlag = 1

        self.addItem(self.pathItem)

    def pen_mouseMoveEvent(self, event):
        self.currentPos = event.scenePos()
        self.path.lineTo(self.currentPos)
        self.pathItem.setPath(self.path)

    def pen_mouseReleaseEvent(self, event):
        self.removeItem(self.pathItem)
        if self.highlightFlag == 0:
            command = CommandPen(self, self.path)
        else:
            command = CommandHighlight(self, self.path)
        self.highlightFlag = 0
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

    def zoom_mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.parent().scale(0.8, 0.8)
        else:
            self.parent().scale(1.25, 1.25)
        self.parent().centerOn(event.scenePos())

    def delta_mousePressEvent(self, event):
        pt = event.scenePos()
        command = CommandDelta(self, pt, self.markDelta)
        self.undoStack.push(command)
