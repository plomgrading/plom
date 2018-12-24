__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__credits__ = ['Andrew Rechnitzer', 'Colin MacDonald', 'Elvis Cai', 'Matt Coles']
__license__ = "GPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QPainter
from PyQt5.QtWidgets import QGraphicsView
# Import the pagescene class.
from pagescene import PageScene


class PageView(QGraphicsView):
    """Extend the graphicsview so that it can pass undo/redo
    comments, delta-marks, save and zoom in /out
    """
    def __init__(self, parent, imgName):
        # init the qgraphicsview
        super(PageView, self).__init__(parent)
        # Set scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # set the area outside the groupimage to be dark-cyan.
        self.setBackgroundBrush(QBrush(Qt.darkCyan))
        # Nice antialiasing and scaling of objects (esp the groupimage)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Init the pagescene with the groupimage
        self.scene = PageScene(self, imgName)
        self.setScene(self.scene)
        # Set the starting mode to pan
        self.setMode("pan")

    def resizeEvent(self, e):
        # On resize used to resize the image to keep it all in view
        self.fitInView(self.scene.imageItem, Qt.KeepAspectRatio)
        super(PageView, self).resizeEvent(e)

    def setMode(self, mode):
        # Set the mode in the pagescene.
        self.scene.mode = mode
        # If mode is pan, then that is handled in the view
        # by turning on drag-mode.
        # remember to turn it off when leaving pan-mode.
        if mode == 'pan':
            self.setDragMode(1)
        else:
            self.setDragMode(0)

    def makeComment(self, dlt, text):
        self.setDragMode(0)
        # Pass the comment and delta on to the pagescene.
        self.scene.mode = 'comment'
        self.scene.commentDelta = int(dlt)
        self.scene.commentText = text

    def markDelta(self, delta):
        self.setDragMode(0)
        # Pass the delta on to the pagescene.
        self.scene.mode = 'delta'
        self.scene.markDelta = delta

    def undo(self):
        self.scene.undoStack.undo()

    def redo(self):
        self.scene.undoStack.redo()

    def save(self):
        self.scene.save()

    def zoomIn(self):
        self.scale(1.25, 1.25)

    def zoomOut(self):
        self.scale(0.8, 0.8)
