__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer"]
__license__ = "AGPLv3"

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QPushButton,
    QTabWidget,
    QWidget,
)
from uiFiles.ui_test_view import Ui_TestView
from examviewwindow import ExamViewWindow


class TestView(QWidget):
    def __init__(self, parent, pageNames, pages):
        super(TestView, self).__init__()
        self.parent = parent
        self.numberOfPages = len(pages)
        self.pageList = pages
        self.pageNames = pageNames
        self.ui = Ui_TestView()
        self.ui.setupUi(self)
        self.connectButtons()
        self.tabs = {}
        self.buildTabs()
        self.show()

    def connectButtons(self):
        self.ui.prevGroupButton.clicked.connect(self.previousTab)
        self.ui.nextGroupButton.clicked.connect(self.nextTab)
        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.maxNormButton.clicked.connect(self.swapMaxNorm)

    def buildTabs(self):
        for k in range(0, self.numberOfPages):
            self.tabs[k] = ExamViewWindow(self.pageList[k])
            self.ui.groupViewTabWidget.addTab(
                self.tabs[k], "Page {}".format(self.pageNames[k])
            )

    def nextTab(self):
        t = self.ui.groupViewTabWidget.currentIndex() + 1
        if t >= self.ui.groupViewTabWidget.count():
            t = 0
        self.ui.groupViewTabWidget.setCurrentIndex(t)

    def previousTab(self):
        t = self.ui.groupViewTabWidget.currentIndex() - 1
        if t < 0:
            t = self.ui.groupViewTabWidget.count() - 1
        self.ui.groupViewTabWidget.setCurrentIndex(t)

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def closeEvent(self, event):
        self.closeWindow()

    def closeWindow(self):
        self.close()


class GroupView(QDialog):
    def __init__(self, fnames):
        super(GroupView, self).__init__()
        grid = QGridLayout()
        self.testImg = ExamViewWindow(fnames)
        self.closeButton = QPushButton("&Close")
        self.maxNormButton = QPushButton("Max/Norm")
        grid.addWidget(self.testImg, 1, 1, 6, 6)
        grid.addWidget(self.closeButton, 7, 7)
        grid.addWidget(self.maxNormButton, 1, 7)
        self.setLayout(grid)
        self.closeButton.clicked.connect(self.closeWindow)
        self.maxNormButton.clicked.connect(self.swapMaxNorm)

        self.show()

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def closeEvent(self, event):
        self.closeWindow()

    def closeWindow(self):
        self.close()


class WholeTestView(QDialog):
    def __init__(self, fnames):
        super(WholeTestView, self).__init__()
        self.pageList = fnames
        self.numberOfPages = len(fnames)
        grid = QGridLayout()
        self.pageTabs = QTabWidget()
        self.tabs = {}
        self.closeButton = QPushButton("&Close")
        self.maxNormButton = QPushButton("&Max/Norm")
        self.pButton = QPushButton("&Previous")
        self.nButton = QPushButton("&Next")
        grid.addWidget(self.pageTabs, 1, 1, 6, 6)
        grid.addWidget(self.pButton, 7, 1)
        grid.addWidget(self.nButton, 7, 2)
        grid.addWidget(self.closeButton, 7, 7)
        grid.addWidget(self.maxNormButton, 1, 7)
        self.setLayout(grid)
        self.pButton.clicked.connect(self.previousTab)
        self.nButton.clicked.connect(self.nextTab)
        self.closeButton.clicked.connect(self.closeWindow)
        self.maxNormButton.clicked.connect(self.swapMaxNorm)
        self.show()
        self.buildTabs()

    def swapMaxNorm(self):
        """Toggles the window size between max and normal"""
        if self.windowState() != Qt.WindowMaximized:
            self.setWindowState(Qt.WindowMaximized)
        else:
            self.setWindowState(Qt.WindowNoState)

    def closeEvent(self, event):
        self.closeWindow()

    def closeWindow(self):
        self.close()

    def nextTab(self):
        t = self.pageTabs.currentIndex() + 1
        if t >= self.pageTabs.count():
            t = 0
        self.pageTabs.setCurrentIndex(t)

    def previousTab(self):
        t = self.pageTabs.currentIndex() - 1
        if t < 0:
            t = self.pageTabs.count() - 1
        self.pageTabs.setCurrentIndex(t)

    def buildTabs(self):
        for k in range(0, self.numberOfPages):
            self.tabs[k] = ExamViewWindow(self.pageList[k])
            self.pageTabs.addTab(self.tabs[k], "{}".format(k + 1))
