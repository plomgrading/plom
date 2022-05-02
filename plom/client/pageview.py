# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView
from plom.client.backGrid import BackGrid


class PageView(QGraphicsView):
    """
    Manages the mutable aspects of viewing the paper.

    Extend the graphicsview so that it can pass undo/redo
    comments, delta-marks, save and zoom in /out.
    """

    def __init__(self, parent):
        """
        Initializes a new pageView object.

        Args:
            parent (Annotator): The Annotator creating the pageview.
                Must have various zoom-related functions available.
            username (str): The username of the marker

        """
        super().__init__(parent)
        self._annotr = parent
        # Set scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # set the area outside the groupimage to be tiled grid image
        self.setStyleSheet("background: transparent")
        self.setBackgroundBrush(BackGrid())

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        # the graphics view accepts drag/drop from the comment list
        self.setAcceptDrops(True)
        self.paperWindow = None

    def connectScene(self, scene):
        """
        Connects a pagescene to the current pageview.

        Args:
            scene (PageScene): the scene to be connected to.

        Returns:
            None

        """
        self.setScene(scene)
        self.fitInView(self.scene().underImage, Qt.KeepAspectRatio)
        # the current view
        self.paperWindow = self.mapToScene(
            self.viewport().contentsRect()
        ).boundingRect()

    def resizeEvent(self, event):
        """
        Resizes the paper.

        Notes:
            Overrides Base Method.
            Currently unused.

        Args:
            event (QEvent) - the event to be resized.
        """
        self._annotr.zoomCBChanged()
        # then any other stuff needed by parent class
        super().resizeEvent(event)

    def setZoomSelector(self, update=False):
        """
        Sets Zoom combo box to show current selection.

        Args:
            update (bool): True if combo box needs updating, False otherwise.

        Returns:
            None
        """
        # sets the current view rect
        self.paperWindow = self.mapToScene(
            self.viewport().contentsRect()
        ).boundingRect()
        if update:
            self._annotr.changeCBZoom(0)

    def zoomIn(self):
        """Zooms in the paper 1.25 x"""
        self._zoomHelper(1.25)

    def zoomOut(self):
        """Zooms out the paper 0.8 x"""
        self._zoomHelper(0.8)

    def _zoomHelper(self, modifier):
        self.scale(modifier, modifier)
        self.setZoomSelector(True)

    def zoomToggle(self):
        """
        Toggles zoom setting between Fit Height and Fit Width.

        If current zoom is Fit Width, changes to Fit Height.
        If current zoom is Fit Height, changes to Fit Width.

        Returns:
            None
        """

        if self._annotr.isZoomFitWidth():
            self.zoomFitHeight(True)
        elif self._annotr.isZoomFitHeight():
            self.zoomFitWidth(True)
        else:
            self.zoomFitWidth(True)

    def zoomFitPage(self, update=False):
        """
        Zooms such that the entire page is visible.

        Args:
            update (bool): True if combo box needs updating, False otherwise.

        Returns:
            None

        """
        # first recompute the scene rect in case anything in the margins.

        tempPaperWindow = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        self.scene().updateSceneRectangle()
        if (
            self.scene().height() / tempPaperWindow.height()
            > self.scene().width() / tempPaperWindow.width()
        ):
            self.zoomFitHeight(False)
        else:
            self.zoomFitWidth(False)
        if update:
            self._annotr.changeCBZoom(1)

    def zoomFitHeight(self, update=True):
        """
        Changes the zoom to fit height.

        Args:
            update (bool): True if combo box needs updating, False otherwise.

        Returns:
            None
        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        tempPaperWindow = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        ratio = tempPaperWindow.height() / self.scene().height() * 0.98
        self.scale(ratio, ratio)
        # Issue #1768: at least initially we should start at the left of the page
        # self.centerOn(self.paperWindow.center())
        self.centerOn(self.paperWindow.left(), self.paperWindow.center().y())
        if update:
            self._annotr.changeCBZoom(3)

    def zoomFitWidth(self, update=True):
        """
        Changes the zoom to fit width.

        Args:
            update (bool): True if combo box needs updating, False otherwise.

        Notes:
            scale to full width, but move center to user-zoomed center

        Returns:
            None
        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        tempPaperWindow = self.mapToScene(self.viewport().contentsRect()).boundingRect()
        rat = tempPaperWindow.width() / self.scene().width() * 0.98
        self.scale(rat, rat)
        # Issue #1768: at least initially we should start at the top of the page
        # self.centerOn(self.paperWindow.center())
        self.centerOn(self.paperWindow.center().x(), self.paperWindow.top())
        if update:
            self._annotr.changeCBZoom(2)

    def zoomToScale(self, scale):
        """
        Zooms to a desired scale with original aspect ratio.

        Args:
            scale (float): the ratio to be scaled to. (1 = 100%, 1.5 = 150% etc)

        Returns:
            None

        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        self.resetTransform()
        self.scale(scale, scale)
        self.centerOn(self.paperWindow.center())
        self.setZoomSelector(False)

    def zoomPrevious(self):
        """
        Zooms to fit the paper window to the view at the current aspect ratio.

        Notes:
            Currently Unused

        Returns:
            None

        """
        self.fitInView(self.paperWindow, Qt.KeepAspectRatio)
        self._annotr.changeCBZoom(0)

    def initializeZoom(self, initRect):
        """
        Initializes zoom upon startup.

        Args:
            initRect (QRectF): the rectangle to be initialized with.

        Returns:
            None

        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        if initRect is None:
            self.fitInView(self.scene().underImage, Qt.KeepAspectRatio)
        else:
            self.fitInView(initRect, Qt.KeepAspectRatio)
        self.setZoomSelector()

    def getCurrentViewRect(self):
        """
        Returns:
            (QRect): the current view rectangle
        """
        return self.mapToScene(self.viewport().contentsRect()).boundingRect()

    def panThrough(self, dy=0.8):
        """
        Pans through the view.

        Args:
            dy (float): amount to adjust by in each scroll.

        Returns:
            None
        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        horizSliderPos = self.horizontalScrollBar().value()
        vertSliderPos = self.verticalScrollBar().value()
        # if not at bottom of view, step down via scrollbar
        if vertSliderPos < self.verticalScrollBar().maximum():
            self.verticalScrollBar().setValue(
                int(vertSliderPos + self.verticalScrollBar().pageStep() * dy)
            )
        else:
            # else move up to top of view
            self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())
            # if not at right of view, step right via scrollbar
            if horizSliderPos < self.horizontalScrollBar().maximum():
                self.horizontalScrollBar().setValue(
                    horizSliderPos + self.horizontalScrollBar().pageStep()
                )
            else:
                # else move back to origin.
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().minimum()
                )

        self.setZoomSelector()

    def depanThrough(self, dy=0.8):
        """
        Depans through the view.

        Args:
            dy (float): amount to adjust by in each scroll.

        Returns:
            None

        """
        # first recompute the scene rect in case anything in the margins.
        self.scene().updateSceneRectangle()

        horizSliderPos = self.horizontalScrollBar().value()
        verticalSliderPos = self.verticalScrollBar().value()
        # if not at bottom of view, step down via scrollbar
        if verticalSliderPos > 0:
            self.verticalScrollBar().setValue(
                int(verticalSliderPos - self.verticalScrollBar().pageStep() * dy)
            )
        else:
            # else move up to top of view
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            # if not at right of view, step right via scrollbar
            if horizSliderPos > 0:
                self.horizontalScrollBar().setValue(
                    horizSliderPos - self.horizontalScrollBar().pageStep()
                )
            else:
                # else move back to origin.
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().maximum()
                )

        self.setZoomSelector()
