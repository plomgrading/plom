# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from plom.client.examviewwindow import ImageViewWidget


class ActionTab(QWidget):
    def __init__(self, parent):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
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
        super().__init__()
        self.parent = parent
        self.test = test
        self.page = page

        self.initUI([onames], [fnames])
        self.action = ""

    def initUI(self, onames, fnames):
        self.viewO = ImageViewWidget(self, onames)
        self.viewC = ImageViewWidget(self, fnames)

        self.cancelB = QPushButton("&cancel")

        self.cancelB.clicked.connect(self.reject)

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
        t0 = ActionTab(self)
        t1 = OriginalTab(self)
        t2 = CollideTab(self)
        self.optionTW.addTab(t0, "Actions")
        self.optionTW.addTab(t1, "Keep original")
        self.optionTW.addTab(t2, "Keep collide")

    def viewWholeTest(self):
        self.parent.viewWholeTest(self.test)
