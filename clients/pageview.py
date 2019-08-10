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

        # the current view
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def resizeEvent(self, e):
        # re-zoom
        self.parent.zoomCBChanged()
        # then any other stuff needed by parent class
        super(PageView, self).resizeEvent(e)

    def setMode(self, mode):
        # Set the mode in the pagescene.
        self.scene.mode = mode
        # if current mode is not comment, make sure the ghostcomment is
        # removed from the scene.
        if mode != "comment":
            self.scene.hideGhost()
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
        self.scene.updateGhost(dlt, text)

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

    def areThereAnnotations(self):
        return self.scene.areThereAnnotations()

    def save(self):
        self.scene.save()

    def latexAFragment(self, txt):
        cur = self.cursor()
        self.setCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()  # this triggers a cursor update
        ret = self.parent.latexAFragment(txt)
        self.setCursor(cur)
        return ret

    def zoomNull(self, update=False):
        # sets the current view rect
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        if update:
            self.parent.changeCBZoom(0)

    def zoomIn(self):
        self.scale(1.25, 1.25)
        self.zoomNull(True)

    def zoomOut(self):
        self.scale(0.8, 0.8)
        self.zoomNull(True)

    def zoomToggle(self):
        # cycle the zoom state setting between width and height
        if self.parent.ui.zoomCB.currentText() == "Fit Width":
            self.zoomHeight(True)
        elif self.parent.ui.zoomCB.currentText() == "Fit Height":
            self.zoomWidth(True)
        else:
            self.zoomWidth(True)

    def zoomAll(self, update=False):
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        if self.scene.height() / crect.height() > self.scene.width() / crect.width():
            self.zoomHeight(False)
        else:
            self.zoomWidth(False)
        if update:
            self.parent.changeCBZoom(1)

    def zoomHeight(self, update=True):
        # scale to full height, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        rat = crect.height() / self.scene.height()
        self.scale(rat, rat)
        self.centerOn(self.vrect.center())
        if update:
            self.parent.changeCBZoom(3)

    def zoomWidth(self, update=True):
        # scale to full width, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        rat = crect.width() / self.scene.width()
        self.scale(rat, rat)
        self.centerOn(self.vrect.center())
        if update:
            self.parent.changeCBZoom(2)

    def zoomReset(self, rat):
        # reset the view to 1:1 but center on current vrect
        self.resetTransform()
        self.scale(rat, rat)
        self.centerOn(self.vrect.center())
        self.zoomNull(False)

    def zoomPrevious(self):
        self.fitInView(self.vrect, Qt.KeepAspectRatio)
        self.parent.changeCBZoom(0)

    def initialZoom(self, initRect):
        if initRect is None:
            self.fitInView(self.scene.imageItem, Qt.KeepAspectRatio)
        else:
            self.fitInView(initRect, Qt.KeepAspectRatio)
        self.zoomNull()

    def checkAllObjectsInside(self):
        return self.scene.checkAllObjectsInside()
