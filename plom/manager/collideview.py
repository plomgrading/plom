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
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from plom.client.examviewwindow import ExamViewWindow


class ActionTab(QWidget):
    def __init__(self, parent):
        super(ActionTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.ob = QPushButton("Keep original page (left)")
        self.cb = QPushButton("Keep colliding page (right)")
        self.vwtb = QPushButton("View whole test")
        vb.addWidget(self.ob)
        vb.addWidget(self.cb)
        vb.addWidget(self.vwtb)
        self.setLayout(vb)
        self.show()
        self.ob.clicked.connect(self.originalPage)
        self.cb.clicked.connect(self.collidingPage)
        self.vwtb.clicked.connect(self.test)

    def originalPage(self):
        self.parent.optionTW.setCurrentIndex(1)
        self.parent.collideGB.setEnabled(False)
        self.parent.collideGB.setStyleSheet("background: red")
        self.parent.originalGB.setStyleSheet("background: green")

    def collidingPage(self):
        self.parent.optionTW.setCurrentIndex(2)
        self.parent.originalGB.setEnabled(False)
        self.parent.collideGB.setStyleSheet("background: green")
        self.parent.originalGB.setStyleSheet("background: red")

    def test(self):
        self.parent.viewWholeTest()


class OriginalTab(QWidget):
    def __init__(self, parent):
        super(OriginalTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.kb = QPushButton("Click to confirm keep original")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.kb)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.kb.clicked.connect(self.keepOriginal)
        self.ob.clicked.connect(self.other)

    def keepOriginal(self):
        self.parent.action = "original"
        self.parent.accept()

    def other(self):
        self.parent.optionTW.setCurrentIndex(0)
        self.parent.collideGB.setEnabled(True)
        self.parent.collideGB.setStyleSheet("")
        self.parent.originalGB.setStyleSheet("")


class CollideTab(QWidget):
    def __init__(self, parent):
        super(CollideTab, self).__init__()
        self.parent = parent
        vb = QVBoxLayout()
        self.kb = QPushButton("Click to confirm replace")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.kb)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.show()
        self.kb.clicked.connect(self.keepCollide)
        self.ob.clicked.connect(self.other)

    def keepCollide(self):
        self.parent.action = "collide"
        self.parent.accept()

    def other(self):
        self.parent.optionTW.setCurrentIndex(0)
        self.parent.originalGB.setEnabled(True)
        self.parent.collideGB.setStyleSheet("")
        self.parent.originalGB.setStyleSheet("")


class CollideViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, onames, fnames, test, page):
        QWidget.__init__(self)
        self.parent = parent
        self.test = test
        self.page = page

        self.initUI([onames], [fnames])
        self.action = ""

    def initUI(self, onames, fnames):
        self.viewO = ExamViewWindow(onames)
        self.viewC = ExamViewWindow(fnames)

        self.cancelB = QPushButton("&cancel")
        self.maxNormB = QPushButton("&max/norm")

        self.cancelB.clicked.connect(self.reject)
        self.maxNormB.clicked.connect(self.swapMaxNorm)

        self.originalGB = QGroupBox("Original")
        self.collideGB = QGroupBox("Collision")
        self.optionTW = QTabWidget()
        self.initTabs()

        ob = QHBoxLayout()
        ob.addWidget(self.viewO)
        self.originalGB.setLayout(ob)
        cb = QHBoxLayout()
        cb.addWidget(self.viewC)
        self.collideGB.setLayout(cb)

        grid = QGridLayout()
        grid.addWidget(self.maxNormB, 1, 4)
        grid.addWidget(self.cancelB, 10, 4)
        grid.addWidget(self.optionTW, 2, 1, 8, 4)
        self.pane = QWidget()
        self.pane.setLayout(grid)

        hb = QHBoxLayout()
        hb.addWidget(self.originalGB)
        hb.setStretchFactor(self.originalGB, 1)
        hb.addWidget(self.collideGB)
        hb.setStretchFactor(self.collideGB, 1)
        hb.addWidget(self.pane)
        self.setLayout(hb)
        self.show()

    def initTabs(self):
        self.t0 = ActionTab(self)
        self.t1 = OriginalTab(self)
        self.t2 = CollideTab(self)
        self.optionTW.addTab(self.t0, "Actions")
        self.optionTW.addTab(self.t1, "Keep original")
        self.optionTW.addTab(self.t2, "Keep collide")

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def viewWholeTest(self):
        self.parent.viewWholeTest(self.test)
