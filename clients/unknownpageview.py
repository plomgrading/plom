__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
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
        self.db = QPushButton("Discard Page")
        self.eb = QPushButton("Extra Page")
        self.tb = QPushButton("Test Page")
        vb.addWidget(self.eb)
        vb.addWidget(self.tb)
        vb.addWidget(self.db)
        self.setLayout(vb)
        self.show()
        self.db.clicked.connect(self.discard)
        self.eb.clicked.connect(self.extra)
        self.tb.clicked.connect(self.test)

    def discard(self):
        self.parent.optionTW.setCurrentIndex(3)

    def extra(self):
        self.parent.optionTW.setCurrentIndex(1)

    def test(self):
        self.parent.optionTW.setCurrentIndex(2)


class DiscardTab(QWidget):
    def __init__(self, parent):
        super(DiscardTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.db = QPushButton("Click to confirm discard")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.db)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.db.clicked.connect(self.discard)
        self.ob.clicked.connect(self.other)

    def discard(self):
        self.parent.action = "discard"
        self.parent.accept()

    def other(self):
        self.parent.optionTW.setCurrentIndex(0)


class ExtraTab(QWidget):
    def __init__(self, parent, maxT, maxQ):
        super(ExtraTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        fl = QFormLayout()
        self.frm = QFrame()
        self.ob = QPushButton("Return to other options")
        self.tsb = QSpinBox()
        self.qsb = QSpinBox()
        self.tsb.setMinimum(1)
        self.tsb.setMaximum(maxT)
        self.qsb.setMinimum(1)
        self.qsb.setMaximum(maxQ)
        self.cb = QPushButton("Click to confirm")
        self.vqb = QPushButton("View that question")
        self.vwb = QPushButton("View whole test")
        fl.addRow(QLabel("Test number:"), self.tsb)
        fl.addRow(QLabel("Question number:"), self.qsb)
        fl.addRow(self.vqb)
        fl.addRow(self.vwb)
        fl.addRow(self.cb)
        self.frm.setLayout(fl)
        vb.addWidget(self.frm)
        vb.addStretch(1)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.vqb.clicked.connect(self.viewQuestion)
        self.vwb.clicked.connect(self.viewWholeTest)
        self.cb.clicked.connect(self.confirm)
        self.ob.clicked.connect(self.other)

    def confirm(self):
        self.parent.action = "extra"
        self.parent.tptq = [self.tsb.value(), self.qsb.value()]
        self.parent.accept()

    def viewQuestion(self):
        self.parent.viewQuestion(self.tsb.value(), self.qsb.value())

    def viewWholeTest(self):
        self.parent.viewWholeTest(self.tsb.value())

    def other(self):
        self.parent.optionTW.setCurrentIndex(0)


class TestTab(QWidget):
    def __init__(self, parent, maxT, maxP):
        super(TestTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        fl = QFormLayout()
        self.frm = QFrame()
        self.ob = QPushButton("Return to other options")
        self.tsb = QSpinBox()
        self.psb = QSpinBox()
        self.tsb.setMinimum(1)
        self.tsb.setMaximum(maxT)
        self.psb.setMinimum(1)
        self.psb.setMaximum(maxP)
        self.cb = QPushButton("Click to confirm")
        self.cpb = QPushButton("Check that page")
        self.vwb = QPushButton("View whole test")
        fl.addRow(QLabel("Test number:"), self.tsb)
        fl.addRow(QLabel("Page number:"), self.psb)
        fl.addRow(self.cpb)
        fl.addRow(self.vwb)
        fl.addRow(self.cb)
        self.frm.setLayout(fl)
        vb.addWidget(self.frm)
        vb.addStretch(1)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.cpb.clicked.connect(self.checkPage)
        self.vwb.clicked.connect(self.viewWholeTest)
        self.cb.clicked.connect(self.confirm)
        self.ob.clicked.connect(self.other)

    def confirm(self):
        self.parent.action = "test"
        self.parent.tptq = [self.tsb.value(), self.psb.value()]
        self.parent.accept()

    def checkPage(self):
        self.parent.checkPage(self.tsb.value(), self.psb.value())

    def viewWholeTest(self):
        self.parent.viewWholeTest(self.tsb.value())

    def other(self):
        self.parent.optionTW.setCurrentIndex(0)


class UnknownViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, tpq):
        QWidget.__init__(self)
        self.parent = parent
        self.numberOfTests = tpq[0]
        self.numberOfPages = tpq[1]
        self.numberOfQuestions = tpq[2]

        if type(fnames) == list:
            self.initUI(fnames)
        else:
            self.initUI([fnames])
        self.action = ""
        self.tptq = []

    def initUI(self, fnames):
        # Grab an UnknownView widget (QGraphicsView)
        self.view = UnknownView(fnames)
        # Render nicely
        self.view.setRenderHint(QPainter.HighQualityAntialiasing)
        self.optionTW = QTabWidget()

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")
        self.rotatePlusB = QPushButton("rotate +90")
        self.rotateMinusB = QPushButton("rotate -90")
        self.cancelB = QPushButton("&cancel")
        self.maxNormB = QPushButton("&max/norm")

        self.cancelB.clicked.connect(self.reject)
        self.resetB.clicked.connect(lambda: self.view.resetView())
        self.rotatePlusB.clicked.connect(self.rotatePlus)
        self.rotateMinusB.clicked.connect(self.rotateMinus)
        self.maxNormB.clicked.connect(self.swapMaxNorm)

        self.resetB.setAutoDefault(False)  # return wont click the button by default.
        self.rotatePlusB.setAutoDefault(False)
        self.rotateMinusB.setAutoDefault(False)

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 6)
        grid.addWidget(self.optionTW, 2, 17, 8, 4)
        grid.addWidget(self.resetB, 20, 1)
        grid.addWidget(self.rotatePlusB, 20, 2)
        grid.addWidget(self.rotateMinusB, 20, 3)
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
        self.t1 = ExtraTab(self, self.numberOfTests, self.numberOfQuestions)
        self.t2 = TestTab(self, self.numberOfTests, self.numberOfPages)
        self.t3 = DiscardTab(self)
        self.optionTW.addTab(self.t0, "Actions")
        self.optionTW.addTab(self.t1, "Extra Page")
        self.optionTW.addTab(self.t2, "Test Page")
        self.optionTW.addTab(self.t3, "Discard")

    def rotatePlus(self):
        self.theta += 90
        if self.theta == 360:
            self.theta = 0
        self.view.rotateImage(90)

    def rotateMinus(self):
        self.theta -= 90
        if self.theta == -90:
            self.theta = 270
        self.view.rotateImage(-90)

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def viewQuestion(self, testNumber, questionNumber):
        self.parent.viewQuestion(testNumber, questionNumber)

    def viewWholeTest(self, testNumber):
        self.parent.viewWholeTest(testNumber)

    def checkPage(self, testNumber, pageNumber):
        self.parent.checkPage(testNumber, pageNumber)


class UnknownView(QGraphicsView):
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
            0, 0, max(1000, br.width()), max(1000, br.height()),
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
