__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QPainter, QCursor
from PyQt5.QtWidgets import QGraphicsView, QApplication

# Import the pagescene class.
from pagescene import PageScene
import time


class PageView(QGraphicsView):
    """Extend the graphicsview so that it can pass undo/redo
    comments, delta-marks, save and zoom in /out
    """

    def __init__(self, parent, imgName):
        # init the qgraphicsview
        super(PageView, self).__init__(parent)
        self.parent = parent
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
        self.fitInView(self.scene.imageItem, Qt.KeepAspectRatio)

        # the graphics view accepts drag/drop from the comment list
        self.setAcceptDrops(True)
        # Set the starting mode to pan
        self.setMode("pan")

        # set flag so can cycle through zoom states
        self.zoomState = 0  # this is user-chosen view
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def resizeEvent(self, e):
        # On resize keep redefine view-rect
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        super(PageView, self).resizeEvent(e)

    def setMode(self, mode):
        # Set the mode in the pagescene.
        self.scene.mode = mode
        # If mode is pan, then that is handled in the view
        # by turning on drag-mode.
        # remember to turn it off when leaving pan-mode.
        if mode == "pan":
            self.setDragMode(1)
        else:
            self.setDragMode(0)

    def makeComment(self, dlt, text):
        self.setDragMode(0)
        # Pass the comment and delta on to the pagescene.
        self.scene.mode = "comment"
        self.scene.commentDelta = int(dlt)
        self.scene.commentText = text

    def markDelta(self, delta):
        self.setDragMode(0)
        # Pass the delta on to the pagescene.
        self.scene.mode = "delta"
        self.scene.markDelta = delta

    def undo(self):
        self.scene.undoStack.undo()

    def redo(self):
        self.scene.undoStack.redo()

    def getComments(self):
        return self.scene.getComments()

    def countComments(self):
        return self.scene.countComments()

    def save(self):
        self.scene.save()

    def latexAFragment(self, txt):
        cur = self.cursor()
        self.setCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()  # this triggers a cursor update
        ret = self.parent.latexAFragment(txt)
        self.setCursor(cur)
        return ret

    def zoomNull(self):
        self.zoomState = 0
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def zoomIn(self):
        self.scale(1.25, 1.25)
        self.zoomNull()

    def zoomOut(self):
        self.scale(0.8, 0.8)
        self.zoomNull()

    def zoomCycle(self):
        # cycle the zoom state setting
        self.zoomState = (self.zoomState + 1) % 3
        if self.zoomState == 0:
            self.zoomPrevious()
        elif self.zoomState == 1:
            self.zoomWidth()
        else:
            self.zoomHeight()

    def zoomHeight(self):
        # scale to full height, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        nrect = crect
        rat = self.scene.height() / crect.height()
        nrect.setHeight(self.scene.height())
        nrect.setWidth(crect.width() * rat)
        nrect.moveCenter(self.vrect.center())
        self.fitInView(nrect)

    def zoomWidth(self):
        # scale to full width, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        nrect = crect
        rat = self.scene.width() / crect.width()
        nrect.setWidth(self.scene.width())
        nrect.setHeight(crect.height() * rat)
        nrect.moveCenter(self.vrect.center())
        self.fitInView(nrect)

    def zoomPrevious(self):
        self.fitInView(self.vrect)

    def initialZoom(self, initRect):
        self.fitInView(initRect)
        self.zoomNull()
