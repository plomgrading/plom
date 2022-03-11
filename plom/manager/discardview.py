# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from plom.client import ImageViewWidget


class ActionTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.ub = QPushButton("Move to unknown pages")
        self.nb = QPushButton("No action")
        vb.addWidget(self.ub)
        vb.addStretch(0)
        vb.addWidget(self.nb)
        vb.addStretch(0)
        self.setLayout(vb)
        self.ub.clicked.connect(self.unknown)
        self.nb.clicked.connect(self.noaction)

    def unknown(self):
        self._parent.optionTW.setCurrentIndex(1)

    def noaction(self):
        self._parent.action = "none"
        self._parent.accept()


class UnknownTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.ub = QPushButton("Click to confirm move to unknown")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.ub)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.ub.clicked.connect(self.unknown)
        self.ob.clicked.connect(self.other)

    def unknown(self):
        self._parent.action = "unknown"
        self._parent.accept()

    def other(self):
        self._parent.action = "none"
        self._parent.optionTW.setCurrentIndex(0)


class DiscardViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames):
        super().__init__(parent)
        self.action = "none"
        self.img = ImageViewWidget(
            self, fnames, has_reset_button=False, dark_background=True
        )
        self.optionTW = QTabWidget()

        resetB = QPushButton("reset view")
        cancelB = QPushButton("&cancel")
        cancelB.clicked.connect(self.reject)
        resetB.clicked.connect(lambda: self.img.resetView())

        resetB.setAutoDefault(False)  # return won't click the button by default.

        grid = QGridLayout()
        grid.addWidget(self.img, 1, 1, 10, 10)
        grid.addWidget(self.optionTW, 1, 11, 10, -1)
        grid.addWidget(resetB, 11, 1)
        grid.addWidget(cancelB, 11, 20)
        self.setLayout(grid)
        self.initTabs()

    def initTabs(self):
        t0 = ActionTab(self)
        t1 = UnknownTab(self)
        self.optionTW.addTab(t0, "Actions")
        self.optionTW.addTab(t1, "Move Page")
