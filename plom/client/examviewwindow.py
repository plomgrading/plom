__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QGuiApplication, QPainter, QPixmap
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


class ExamViewWindow(QWidget):
    """Simple view window for pageimages"""

    def __init__(self, fnames=None):
        QWidget.__init__(self)
        if isinstance(fnames, str):
            fnames = [fnames]
        self.initUI(fnames)

    def initUI(self, fnames):
        # Grab an examview widget (QGraphicsView)
        self.view = ExamView(fnames)
        # Render nicely
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # reset view button passes to the examview.
        self.resetB = QPushButton("&reset view")
        self.resetB.clicked.connect(lambda: self.view.resetView())
        self.resetB.setAutoDefault(False)  # return wont click the button by default.
        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 4)
        grid.addWidget(self.resetB, 20, 1)
        self.setLayout(grid)
        self.show()
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
        # update the image
        if type(fnames) == list:
            self.view.updateImage(fnames)
        else:
            self.view.updateImage([fnames])

        # re-set the view transform and scroll values
        self.view.setTransform(self.viewTrans)
        self.view.horizontalScrollBar().setValue(self.dx)
        self.view.verticalScrollBar().setValue(self.dy)

    def resizeEvent(self, whatev):
        """Seems to ensure image gets resize on window resize."""
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

    def __init__(self, fnames):
        QGraphicsView.__init__(self)
        self.initUI(fnames)

    def initUI(self, fnames):
        # set background
        self.setStyleSheet("background: transparent")
        self.setBackgroundBrush(BackGrid())
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Make QGraphicsScene
        self.scene = QGraphicsScene()
        # TODO = handle different image sizes.
        self.images = {}
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImage(fnames)

    def updateImage(self, fnames):
        """Update the image with that from filename"""
        for n in self.images:
            self.imageGItem.removeFromGroup(self.images[n])
            self.images[n].setVisible(False)
        if fnames is not None:
            x = 0
            for (n, fn) in enumerate(fnames):
                pix = QPixmap(fn)
                self.images[n] = QGraphicsPixmapItem(pix)
                self.images[n].setTransformationMode(Qt.SmoothTransformation)
                self.images[n].setPos(x, 0)
                self.images[n].setVisible(True)
                sf = float(ScenePixelHeight) / float(pix.height())
                self.images[n].setScale(sf)
                self.scene.addItem(self.images[n])
                # x += self.images[n].boundingRect().width() + 10
                # TODO: why did this have + 10 but the scene did not?
                x += sf * (pix.width() - 1.0)
                # TODO: don't floor here if units of scene are large!
                x = int(x)
                self.imageGItem.addToGroup(self.images[n])

        # Set sensible sizes and put into the view, and fit view to the image.
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
