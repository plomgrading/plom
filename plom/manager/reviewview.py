# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from plom.client import ExamView


class ActionTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.rb = QPushButton("Review")
        self.nb = QPushButton("No action")
        vb.addWidget(self.rb)
        vb.addStretch(0)
        vb.addWidget(self.nb)
        vb.addStretch(0)
        self.setLayout(vb)
        self.rb.clicked.connect(self.review)
        self.nb.clicked.connect(self.noaction)

    def review(self):
        self._parent.optionTW.setCurrentIndex(1)

    def noaction(self):
        self._parent.action = "none"
        self._parent.accept()


class ReviewTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.rb = QPushButton("Click to confirm review")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.rb)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.rb.clicked.connect(self.review)
        self.ob.clicked.connect(self.other)

    def review(self):
        self._parent.action = "review"
        self._parent.accept()

    def other(self):
        self._parent.action = "none"
        self._parent.optionTW.setCurrentIndex(0)


class ReviewViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, quidto="question"):
        super().__init__(parent)
        self.quidto = quidto
        self.action = "none"
        self.view = ExamView(fnames, dark_background=True)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.optionTW = QTabWidget()

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")
        self.cancelB = QPushButton("&cancel")

        self.cancelB.clicked.connect(self.reject)
        self.resetB.clicked.connect(lambda: self.view.resetView())

        self.resetB.setAutoDefault(False)  # return won't click the button by default.

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 6)
        grid.addWidget(self.optionTW, 1, 11, 10, -1)
        grid.addWidget(self.resetB, 11, 1)
        grid.addWidget(self.cancelB, 11, 20)
        self.setLayout(grid)
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
        self.view.updateImages(fnames)
        # re-set the view transform and scroll values
        self.view.setTransform(self.viewTrans)
        self.view.horizontalScrollBar().setValue(self.dx)
        self.view.verticalScrollBar().setValue(self.dy)

    def initTabs(self):
        t0 = ActionTab(self)
        t1 = ReviewTab(self)
        self.optionTW.addTab(t0, "Actions")
        self.optionTW.addTab(t1, "Review {}".format(self.quidto))
