__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QGuiApplication, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QFormLayout,
    QGraphicsPixmapItem,
    QGraphicsItemGroup,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ActionTab(QWidget):
    def __init__(self, parent):
        super(ActionTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.rb = QPushButton("Review")
        self.nb = QPushButton("No action")
        vb.addWidget(self.rb)
        vb.addStretch(0)
        vb.addWidget(self.nb)
        vb.addStretch(0)
        self.setLayout(vb)
        self.show()
        self.rb.clicked.connect(self.review)
        self.nb.clicked.connect(self.noaction)

    def review(self):
        self.parent.optionTW.setCurrentIndex(1)

    def noaction(self):
        self.parent.action = "none"
        self.parent.accept()


class ReviewTab(QWidget):
    def __init__(self, parent):
        super(ReviewTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.rb = QPushButton("Click to confirm review")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.rb)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.rb.clicked.connect(self.review)
        self.ob.clicked.connect(self.other)

    def review(self):
        self.parent.action = "review"
        self.parent.accept()

    def other(self):
        self.parent.action = "none"
        self.parent.optionTW.setCurrentIndex(0)


class ReviewViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, quidto="question"):
        QWidget.__init__(self)
        self.parent = parent
        self.quidto = quidto

        if type(fnames) == list:
            self.initUI(fnames)
        else:
            self.initUI([fnames])
        self.action = "none"

    def initUI(self, fnames):
        self.view = ReviewView(fnames)
        # Render nicely
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)
        self.optionTW = QTabWidget()

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")
        self.cancelB = QPushButton("&cancel")
        self.maxNormB = QPushButton("&max/norm")

        self.cancelB.clicked.connect(self.reject)
        self.resetB.clicked.connect(lambda: self.view.resetView())
        self.maxNormB.clicked.connect(self.swapMaxNorm)

        self.resetB.setAutoDefault(False)  # return wont click the button by default.

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 6)
        grid.addWidget(self.optionTW, 2, 17, 8, 4)
        grid.addWidget(self.resetB, 20, 1)
        grid.addWidget(self.cancelB, 20, 20)
        grid.addWidget(self.maxNormB, 1, 20)
        self.setLayout(grid)
        self.show()
        # Store the current exam view as a qtransform
        self.viewTrans = self.view.transform()
        self.dx = self.view.horizontalScrollBar().value()
        self.dy = self.view.verticalScrollBar().value()
        self.theta = 0
        self.initTabs()

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

    def initTabs(self):
        self.t0 = ActionTab(self)
        self.t1 = ReviewTab(self)
        self.optionTW.addTab(self.t0, "Actions")
        self.optionTW.addTab(self.t1, "Review {}".format(self.quidto))

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)


class ReviewView(QGraphicsView):
    """Simple extension of QGraphicsView
    - containing an image and click-to-zoom/unzoom
    """

    def __init__(self, fnames):
        QGraphicsView.__init__(self)
        self.initUI(fnames)

    def initUI(self, fnames):
        # Make QGraphicsScene
        self.scene = QGraphicsScene()
        # TODO = handle different image sizes.
        self.images = {}
        self.imageGItem = QGraphicsItemGroup()
        self.scene.addItem(self.imageGItem)
        self.updateImage(fnames)
        self.setBackgroundBrush(QBrush(Qt.darkCyan))

    def updateImage(self, fnames):
        """Update the image with that from filename"""
        for n in self.images:
            self.imageGItem.removeFromGroup(self.images[n])
            self.images[n].setVisible(False)
        if fnames is not None:
            x = 0
            n = 0
            for fn in fnames:
                self.images[n] = QGraphicsPixmapItem(QPixmap(fn))
                self.images[n].setTransformationMode(Qt.SmoothTransformation)
                self.images[n].setPos(x, 0)
                self.images[n].setVisible(True)
                self.scene.addItem(self.images[n])
                x += self.images[n].boundingRect().width() + 10
                self.imageGItem.addToGroup(self.images[n])
                n += 1

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
