import sys
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QPainter
from PyQt5.QtWidgets import QGraphicsView

from pagescene import PageScene

class PageView(QGraphicsView):
    def __init__(self, parent, imgName):
        super(PageView, self).__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setBackgroundBrush(QBrush(Qt.blue))
        self.setRenderHint(QPainter.HighQualityAntialiasing)
        self.scene = PageScene(self, imgName)
        self.setScene(self.scene)
        self.mode = "pen"

    def resizeEvent(self, e):
        self.fitInView(self.scene.imageItem, Qt.KeepAspectRatio)
        super(PageView, self).resizeEvent(e)

    def setMode(self, mode):
        self.scene.mode = mode
        if mode == 'pan':
            self.setDragMode(1)
        else:
            self.setDragMode(0)

    def makeComment(self, item):
        self.scene.mode = 'comment'
        self.scene.commentItem = item
        self.setDragMode(0)

    def markDelta(self, delta):
        self.scene.mode = 'delta'
        self.scene.markDelta = delta
        self.setDragMode(0)


    def undo(self):
        self.scene.undoStack.undo()
    def redo(self):
        self.scene.undoStack.redo()

    def save(self):
        self.scene.save()
