__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import os
import sys
import time
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QCursor, QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsView, QApplication
from plom.client.backGrid import BackGrid


class PageView(QGraphicsView):
    """Extend the graphicsview so that it can pass undo/redo
    comments, delta-marks, save and zoom in /out
    """

    def __init__(self, parent, username=None):
        # init the qgraphicsview
        super(PageView, self).__init__(parent)
        self.parent = parent
        # Set scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # set the area outside the groupimage to be tiled grid png
        self.setBackgroundBrush(QBrush(BackGrid(username)))

        # Nice antialiasing and scaling of objects (esp the groupimage)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # the graphics view accepts drag/drop from the comment list
        self.setAcceptDrops(True)

    def connectScene(self, scene):
        self.setScene(scene)
        self.fitInView(self.scene().underImage, Qt.KeepAspectRatio)
        # the current view
        self.vrect = self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def resizeEvent(self, e):
        # re-zoom
        self.parent.zoomCBChanged()
        # then any other stuff needed by parent class
        super(PageView, self).resizeEvent(e)

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
        if self.parent.isZoomFitWidth():
            self.zoomHeight(True)
        elif self.parent.isZoomFitHeight():
            self.zoomWidth(True)
        else:
            self.zoomWidth(True)

    def zoomAll(self, update=False):
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        if (
            self.scene().height() / crect.height()
            > self.scene().width() / crect.width()
        ):
            self.zoomHeight(False)
        else:
            self.zoomWidth(False)
        if update:
            self.parent.changeCBZoom(1)

    def zoomHeight(self, update=True):
        # scale to full height, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        rat = crect.height() / self.scene().height()
        self.scale(rat, rat)
        self.centerOn(self.vrect.center())
        if update:
            self.parent.changeCBZoom(3)

    def zoomWidth(self, update=True):
        # scale to full width, but move center to user-zoomed center
        crect = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        rat = crect.width() / self.scene().width()
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
            self.fitInView(self.scene().underImage, Qt.KeepAspectRatio)
        else:
            self.fitInView(initRect, Qt.KeepAspectRatio)
        self.zoomNull()

    def getCurrentViewRect(self):
        return self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def panThrough(self, dy=0.8):
        hv = self.horizontalScrollBar().value()
        vv = self.verticalScrollBar().value()
        # if not at bottom of view, step down via scrollbar
        if vv < self.verticalScrollBar().maximum():
            self.verticalScrollBar().setValue(
                vv + self.verticalScrollBar().pageStep() * dy
            )
        else:
            # else move up to top of view
            self.verticalScrollBar().setValue(0)
            # if not at right of view, step right via scrollbar
            if hv < self.horizontalScrollBar().maximum():
                self.horizontalScrollBar().setValue(
                    hv + self.horizontalScrollBar().pageStep()
                )
            else:
                # else move back to origin.
                self.horizontalScrollBar().setValue(0)

        self.zoomNull()

    def depanThrough(self, dy=0.8):
        hv = self.horizontalScrollBar().value()
        vv = self.verticalScrollBar().value()
        # if not at bottom of view, step down via scrollbar
        if vv > 0:
            self.verticalScrollBar().setValue(
                vv - self.verticalScrollBar().pageStep() * dy
            )
        else:
            # else move up to top of view
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            # if not at right of view, step right via scrollbar
            if hv > 0:
                self.horizontalScrollBar().setValue(
                    hv - self.horizontalScrollBar().pageStep()
                )
            else:
                # else move back to origin.
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().maximum()
                )

        self.zoomNull()
