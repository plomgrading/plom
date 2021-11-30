# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QGuiApplication, QBrush, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QPushButton,
    QWidget,
)

from plom import ScenePixelHeight
from plom.client.backGrid import BackGrid


class ImageViewWidget(QWidget):
    """Simple view widget for pageimages to be embedded in other windows."""

    def __init__(self, parent, fnames=None, has_reset_button=True, compact=True):
        super().__init__(parent)
        # Grab an examview widget (QGraphicsView)
        self.view = ExamView(fnames)
        # Render nicely
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if has_reset_button:
            resetB = QPushButton("&reset view")
            resetB.clicked.connect(self.resetView)
            # return won't click the button by default
            resetB.setAutoDefault(False)
        grid = QGridLayout()
        if compact:
            grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.view, 1, 1, 10, 4)
        if has_reset_button:
            grid.addWidget(resetB, 20, 1)
        self.setLayout(grid)
        # Store the current exam view as a qtransform
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()

    def updateImage(self, fnames):
        """Pass file to the view to update the image"""
        # first store the current view transform and scroll values
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()
        self.view.updateImages(fnames)

        # re-set the view transform and scroll values
        self.view.setTransform(self.viewTrans)
        self.view.horizontalScrollBar().setValue(self.dx)
        self.view.verticalScrollBar().setValue(self.dy)

    def resizeEvent(self, whatev):
        """Seems to ensure image gets resize on window resize."""
        self.view.resetView()

    def resetView(self):
        self.view.resetView()

    def forceRedrawOrSomeBullshit(self):
        """Horrid workaround when we cannot get proper redraws.

        Colin (and Andrew) will be very happy with this function is
        refactored away by a Qt expert.  Or even a Qt novice.  Anyone
        with a pulse really.

        This does not seem to crash if you close the dialog before the
        timer fires.  That's the only positive thing I can say about it.
        """
        QTimer.singleShot(32, self.view.resetView)


class ExamView(QGraphicsView):
    """Simple extension of QGraphicsView
    - containing an image and click-to-zoom/unzoom
    """

    def __init__(self, fnames, dark_background=False):
        super().__init__()
        # set background
        if dark_background:
            self.setBackgroundBrush(QBrush(Qt.darkCyan))
        else:
            self.setStyleSheet("background: transparent")
            self.setBackgroundBrush(BackGrid())
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.scene = QGraphicsScene()
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImages(fnames)

    def updateImages(self, fnames):
        """Update the images new ones from filenames

        Args:
            fnames (None/str/list): a list of `pathlib.Path` or `str` of
                image filenames.  Can also be a str, for a single image.
        """
        if isinstance(fnames, str):
            fnames = [fnames]
        for img in self.imageGItem.childItems():
            self.imageGItem.removeFromGroup(img)
            self.scene.removeItem(img)
        img = None

        if fnames is not None:
            x = 0
            for (n, fn) in enumerate(fnames):
                pix = QPixmap(str(fn))
                pixmap = QGraphicsPixmapItem(pix)
                pixmap.setTransformationMode(Qt.SmoothTransformation)
                pixmap.setPos(x, 0)
                pixmap.setVisible(True)
                sf = float(ScenePixelHeight) / float(pix.height())
                pixmap.setScale(sf)
                self.scene.addItem(pixmap)
                self.imageGItem.addToGroup(pixmap)
                # x += pixmap.boundingRect().width() + 10
                # TODO: some tools (manager?) had + 10 (maybe with darkbg?)
                x += sf * (pix.width() - 1.0)
                # TODO: don't floor here if units of scene are large!
                x = int(x)

        # Set sensible sizes and put into the view, and fit view to the image
        br = self.imageGItem.boundingRect()
        self.scene.setSceneRect(
            0,
            0,
            max(1000, br.width()),
            max(1000, br.height()),
        )
        self.setScene(self.scene)
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        """Left/right click to zoom in and out"""
        if (event.button() == Qt.RightButton) or (
            QGuiApplication.queryKeyboardModifiers() == Qt.ShiftModifier
        ):
            self.scale(0.8, 0.8)
        else:
            self.scale(1.25, 1.25)
        self.centerOn(event.pos())

    def resetView(self):
        """Reset the view to its reasonable initial state."""
        self.fitInView(self.imageGItem, Qt.KeepAspectRatio)

    def rotateImage(self, dTheta):
        self.rotate(dTheta)
        self.resetView()
