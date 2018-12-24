__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__credits__ = ['Andrew Rechnitzer', 'Colin MacDonald', 'Elvis Cai']
__license__ = "GPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, \
    QGraphicsView, QGridLayout, QPushButton, QWidget


class ExamViewWindow(QWidget):
    """Simple view window for pageimages"""
    def __init__(self, fname=None):
        QWidget.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        # Grab an examview widget (QGraphicsView)
        self.view = ExamView(fname)
        # Render nicely
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)
        # reset view button passes to the examview.
        self.resetB = QPushButton('reset view')
        self.resetB.clicked.connect(lambda: self.view.resetView())
        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 4)
        grid.addWidget(self.resetB, 20, 1)
        self.setLayout(grid)
        self.show()

    def updateImage(self, fname):
        """Pass file to the view to update the image"""
        self.view.updateImage(fname)


class ExamView(QGraphicsView):
    """Simple extension of QGraphicsView
    - containing an image and click-to-zoom/unzoom
    """
    def __init__(self, fname):
        QGraphicsView.__init__(self)
        self.initUI(fname)

    def initUI(self, fname):
        # Make QGraphicsScene
        self.scene = QGraphicsScene()
        # Pixmap, pixmapitem from the filename, render nicely.
        self.image = QPixmap(fname)
        self.imageItem = QGraphicsPixmapItem(self.image)
        self.imageItem.setTransformationMode(Qt.SmoothTransformation)
        # Set sensible sizes and put into the view, and fit view to the image.
        self.scene.setSceneRect(0, 0, max(1000, self.image.width()),
                                max(1000, self.image.height()))
        self.scene.addItem(self.imageItem)
        self.setScene(self.scene)
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def updateImage(self, fname):
        """Update the image with that from filename"""
        self.image = QPixmap(fname)
        self.imageItem.setPixmap(self.image)
        self.scene.setSceneRect(0, 0, self.image.width(), self.image.height())
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)

    def mouseReleaseEvent(self, event):
        """Left/right click to zoom in and out"""
        if(event.button() == Qt.RightButton):
            self.scale(0.8, 0.8)
        else:
            self.scale(1.25, 1.25)
        self.centerOn(event.pos())

    def resetView(self):
        """Reset the view to its reasonable initial state."""
        self.fitInView(self.imageItem, Qt.KeepAspectRatio)
