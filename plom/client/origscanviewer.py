# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Vala Vakilian

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QBrush, QIcon, QPixmap, QTransform
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QGridLayout,
    QListView,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QToolButton,
)

from .examviewwindow import ExamViewWindow
from .uiFiles.ui_test_view import Ui_TestView
from .useful_classes import SimpleMessage

import os
import sys


class SourceList(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setViewMode(QListWidget.IconMode)
        self.setAcceptDrops(False)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFlow(QListView.LeftToRight)
        self.setIconSize(QSize(320, 320))
        self.setSpacing(8)
        self.setWrapping(False)
        self.itemDoubleClicked.connect(self.viewImage)
        self.item_positions = {}
        self.item_files = {}
        self.setSelectionMode(QListView.SingleSelection)

    def addImageItem(self, p, pfile, belongs):
        current_row = self.count()
        name = str(p)
        it = QListWidgetItem(QIcon(pfile), name)
        if belongs:
            it.setBackground(QBrush(Qt.darkGreen))
        self.addItem(it)  # item is added at current_row
        self.item_positions[name] = current_row
        self.item_files[name] = pfile

    def rotateImage(self, angle=90):
        ci = self.currentItem()
        name = ci.text()
        rot = QTransform()
        rot.rotate(angle)
        rfile = self.item_files[name]

        cpix = QPixmap(rfile)
        npix = cpix.transformed(rot)
        npix.save(rfile, format="PNG")

        ci.setIcon(QIcon(rfile))
        self.parent.update()

    def removeItem(self, name=None):
        if name:
            ci = self.item(self.item_positions[name])
        else:
            ci = self.currentItem()

        if ci is None:
            return None
        ci.setHidden(True)
        self.setCurrentItem(None)
        return ci.text()

    def returnItem(self, name):
        if name is None:  # Issue #1200 workaround
            return
        ci = self.item(self.item_positions[name])
        if ci:
            ci.setHidden(False)

    def viewImage(self, qi):
        self.parent.viewImage(self.item_files[qi.text()])


class SinkList(QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListView.LeftToRight)
        self.setAcceptDrops(False)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFlow(QListView.LeftToRight)
        # self.setResizeMode(QListView.Adjust)
        self.setIconSize(QSize(320, 320))
        self.setSpacing(8)
        self.setWrapping(False)
        self.item_belongs = (
            {}
        )  # whether or not the item 'officially' belongs to the question
        self.item_files = {}
        self.itemDoubleClicked.connect(self.viewImage)
        self.setSelectionMode(QListView.SingleSelection)

    def addPotentialItem(self, p, pfile, belongs):
        name = str(p)
        self.item_files[name] = pfile
        self.item_belongs[name] = belongs

    def removeItem(self):
        cr = self.currentRow()
        ci = self.currentItem()
        if ci is None:
            return None
        elif self.count() == 1:  # cannot remove all pages
            return None
        else:
            ci = self.takeItem(cr)
            self.setCurrentItem(None)
            return ci.text()

    def appendItem(self, name):
        if name is None:
            return
        ci = QListWidgetItem(QIcon(self.item_files[name]), name)
        if self.item_belongs[name]:
            ci.setBackground(QBrush(Qt.darkGreen))
        self.addItem(ci)
        self.setCurrentItem(ci)

    def shuffleLeft(self):
        cr = self.currentRow()
        if cr in [-1, 0]:
            return
        ci = self.takeItem(cr)
        self.insertItem(cr - 1, ci)
        self.setCurrentRow(cr - 1)

    def shuffleRight(self):
        cr = self.currentRow()
        if cr in [-1, self.count() - 1]:
            return
        ci = self.takeItem(cr)
        self.insertItem(cr + 1, ci)
        self.setCurrentRow(cr + 1)

    def reverseOrder(self):
        rc = self.count()
        for n in range(rc // 2):
            # swap item[n] with item [rc-n-1]
            ri = self.takeItem(rc - n - 1)
            li = self.takeItem(n)
            self.insertItem(n, ri)
            self.insertItem(rc - n - 1, li)

    def rotateImage(self, angle=90):
        ci = self.currentItem()
        name = ci.text()
        rot = QTransform()
        rot.rotate(angle)
        rfile = self.item_files[name]

        cpix = QPixmap(rfile)
        npix = cpix.transformed(rot)
        npix.save(rfile, format="PNG")

        ci.setIcon(QIcon(rfile))
        self.parent.update()

    def viewImage(self, qi):
        self.parent.viewImage(self.item_files[qi.text()])

    def getNameList(self):
        nList = []
        for r in range(self.count()):
            nList.append(self.item(r).text())
        return nList


class RearrangementViewer(QDialog):
    def __init__(self, parent, testNumber, pageData, pageFiles, need_to_confirm=False):
        super().__init__()
        self.parent = parent
        self.testNumber = testNumber
        self.need_to_confirm = need_to_confirm
        self._setupUI()
        pageData, pageFiles = self.temp_dedupe_filter(pageData, pageFiles)
        self.pageData = pageData
        self.pageFiles = pageFiles
        self.nameToIrefNFile = {}
        # note pagedata  triples [name, image-ref, true/false, pos_in_current_annotation]
        self.populateList()

    def _setupUI(self):
        """
        Sets up thee UI for the rearrangement Viewer.

        Notes:
             helper method for __init__

        Returns:
            None

        """

        self.scrollA = QScrollArea()
        self.listA = SourceList(self)
        self.scrollA.setWidget(self.listA)
        self.scrollA.setWidgetResizable(True)
        self.scrollB = QScrollArea()
        self.listB = SinkList(self)
        self.scrollB.setWidget(self.listB)
        self.scrollB.setWidgetResizable(True)

        self.appendB = QToolButton()
        self.appendB.setText("Add Page")
        self.appendB.setArrowType(Qt.DownArrow)
        self.appendB.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.removeB = QToolButton()
        self.removeB.setArrowType(Qt.UpArrow)
        self.removeB.setText("Remove Page")
        self.removeB.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.sLeftB = QToolButton()
        self.sLeftB.setArrowType(Qt.LeftArrow)
        self.sLeftB.setText("Shift Left")
        self.sLeftB.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.sRightB = QToolButton()
        self.sRightB.setArrowType(Qt.RightArrow)
        self.sRightB.setText("Shift Right")
        self.sRightB.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.reverseB = QPushButton("Reverse Order")

        try:
            base_path = sys._MEIPASS
        except Exception:
            # a hack - fix soon.
            base_path = os.path.join(os.path.dirname(__file__), "icons")
            # base_path = "./icons"
        self.rotateB_cw = QPushButton(
            QIcon("{}/rotate_clockwise.svg".format(base_path)), ""
        )
        self.rotateB_cw.setText("Rotate CW")
        self.rotateB_ccw = QPushButton(
            QIcon("{}/rotate_counter_clockwise.svg".format(base_path)), ""
        )
        self.rotateB_ccw.setText("Rotate CCW")

        self.closeB = QPushButton("&Close")
        self.acceptB = QPushButton("&Accept")

        self.permute = [False]

        hb1 = QHBoxLayout()
        hb1.addWidget(self.appendB)
        hb1.addWidget(self.removeB)

        hb3 = QHBoxLayout()
        hb3.addWidget(self.rotateB_cw)
        hb3.addWidget(self.rotateB_ccw)
        hb3.addWidget(self.sLeftB)
        hb3.addWidget(self.sRightB)
        hb3.addWidget(self.reverseB)
        hb3.addWidget(self.acceptB)
        hb3.addWidget(self.closeB)

        allPages = QLabel("All Pages in Exam")
        allPages.setAlignment(Qt.AlignCenter)
        thisQuestion = QLabel("Pages for this Question")
        thisQuestion.setAlignment(Qt.AlignCenter)

        vb0 = QVBoxLayout()
        vb0.addWidget(allPages)
        vb0.addWidget(self.scrollA)
        vb0.addLayout(hb1)
        vb0.addWidget(thisQuestion)
        vb0.addWidget(self.scrollB)
        vb0.addLayout(hb3)

        self.setLayout(vb0)
        self.resize(QSize(self.parent.width() / 2, self.parent.height() * 2 / 3))

        self.closeB.clicked.connect(self.close)
        self.sLeftB.clicked.connect(self.shuffleLeft)
        self.sRightB.clicked.connect(self.shuffleRight)
        self.reverseB.clicked.connect(self.reverseOrder)
        self.rotateB_cw.clicked.connect(lambda: self.rotateImage(90))
        self.rotateB_ccw.clicked.connect(lambda: self.rotateImage(-90))
        self.appendB.clicked.connect(self.sourceToSink)
        self.removeB.clicked.connect(self.sinkToSource)
        self.acceptB.clicked.connect(self.doShuffle)

        allPageWidgets = [self.listA, self.listB]

        self.listA.selectionModel().selectionChanged.connect(
            lambda sel, unsel: self.singleSelect(self.listA, allPageWidgets)
        )
        self.listB.selectionModel().selectionChanged.connect(
            lambda sel, unsel: self.singleSelect(self.listB, allPageWidgets)
        )

    def temp_dedupe_filter(self, pageData, pageFiles):
        """A temporary hack for a side branch.  Usually should be a no-op.

        This supports [1] and hopefully does nothing in other cases.

        [1] https://gitlab.com/plom/plom/-/merge_requests/698

        The data looks like the following.  We want to remove False rows that
        have their md5 in one of the True rows:
        ```
        ['h1.1', 'e224c22eda93456143fbac94beb0ffbd', True, 1] /tmp/plom_zq/tmpnqq.image
        ['h1.2', '97521f4122df24ca012a12930391195a', True, 2] /tmp/plom_zq/tmp_om.image
        ['h2.1', 'e224c22eda93456143fbac94beb0ffbd', False, 1] /tmp/plom_zq/tmpx0s.image
        ['h2.2', '97521f4122df24ca012a12930391195a', False, 2] /tmp/plom_zq/tmpd5g.image
        ```
        """
        bottom_md5_list = []
        for x in pageData:
            if x[2]:
                bottom_md5_list.append(x[1])
        new_pageData = []
        new_pageFiles = []
        for x, y in zip(pageData, pageFiles):
            print("debug: {}, {}".format(x, y))
            if x[2]:
                new_pageData.append(x)
                new_pageFiles.append(y)
            else:
                if x[1] not in bottom_md5_list:
                    new_pageData.append(x)
                    new_pageFiles.append(y)
        return new_pageData, new_pageFiles

    def populateList(self):
        """
        Populates the QListWidgets with exam pages.

        Returns:
            None

        """
        # each entry in pagedata = 4-tuple of []
        # page-code = t.pageNumber, h.questionNumber.order, e.questionNumber.order, or l.order
        # image-id-reference number,
        # true/false - if belongs to the given question or not.
        # position in current annotation (or none if not)
        move_order = {}
        for k in range(len(self.pageData)):
            self.nameToIrefNFile[self.pageData[k][0]] = [
                self.pageData[k][1],
                self.pageFiles[k],
            ]
            # add every page image to list A
            self.listA.addImageItem(
                self.pageData[k][0], self.pageFiles[k], self.pageData[k][2]
            )
            # add the potential for every page to listB
            self.listB.addPotentialItem(
                self.pageData[k][0], self.pageFiles[k], self.pageData[k][2]
            )
            # if position in current annot is non-null then add to list of pages to move between lists.
            if self.pageData[k][2] and self.pageData[k][3]:
                move_order[self.pageData[k][3]] = self.pageData[k][0]
        for k in sorted(move_order.keys()):
            self.listB.appendItem(self.listA.removeItem(name=move_order[k]))

    def sourceToSink(self):
        """
        Adds the currently selected page to the list for the current question.

        Notes:
            If currently selected page is in current question, does nothing.

        Returns:
            None

        """
        if self.listA.selectionModel().hasSelection():
            self.listB.appendItem(self.listA.removeItem())
        else:
            pass

    def sinkToSource(self):
        """
        Removes the currently selected page from the list for the current
        question.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if self.listB.selectionModel().hasSelection():
            self.listA.returnItem(self.listB.removeItem())
        else:
            pass

    def shuffleLeft(self):
        """
        Shuffles currently selected page to the left one position.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if self.listB.selectionModel().hasSelection():
            self.listB.shuffleLeft()
        else:
            pass

    def shuffleRight(self):
        """
        Shuffles currently selected page to the left one position.

        Notes:
            If currently selected page isn't in current question,
            does nothing.

        Returns:
            None
        """
        if self.listB.selectionModel().hasSelection():
            self.listB.shuffleRight()
        else:
            pass

    def reverseOrder(self):
        """
        reverses the order of the pages in current question.
        """
        self.listB.reverseOrder()

    def rotateImage(self, angle=90):
        """ Rotates the currently selected page by 90 degrees."""
        if self.listA.selectionModel().hasSelection():
            self.listA.rotateImage(angle)
        elif self.listB.selectionModel().hasSelection():
            self.listB.rotateImage(angle)
        else:
            pass

    def viewImage(self, fname):
        """ Shows a larger view of the currently selected page."""
        ShowExamPage(self, fname)

    def doShuffle(self):
        """
        Reorders and saves pages according to user's selections.

        Returns:

        """
        if self.need_to_confirm:
            msg = SimpleMessage(
                "Are you sure you want to save this page order? This will erase "
                "all your annotations."
            )
            if msg.exec() == QMessageBox.No:
                return

        self.permute = []
        for n in self.listB.getNameList():
            self.permute.append(self.nameToIrefNFile[n])
            # return pairs of [iref, file]
        self.accept()

    def singleSelect(self, currentList, allPages):
        """
        If item selected by user isnt in currentList, deselects currentList.

        Args:
            currentList (QListWidget): the list being checked.
            allPages (List[QListWidget]): all lists in selection

        Notes:
            from https://stackoverflow.com/questions/45509496/qt-multiple-qlistwidgets-and-only-a-single-entry-selected

        Returns:
            None

        """
        for lstViewI in allPages:
            if lstViewI == currentList:
                continue
            # the check is necessary to prevent recursions...
            if lstViewI.selectionModel().hasSelection():
                # ...as this causes emission of selectionChanged() signal as well:
                lstViewI.selectionModel().clearSelection()


class ShowExamPage(QDialog):
    """
    Shows an expanded view of the Exam.
    """

    def __init__(self, parent, fname):
        """
        Initialize new exam page
        Args:
            parent (RearrangementViewer): Parent.
            fname (str): file name

        """
        super(ShowExamPage, self).__init__()
        self.setParent(parent)
        self.setWindowFlags(Qt.Dialog)
        grid = QGridLayout()
        self.testImg = ExamViewWindow(fname)
        self.closeButton = QPushButton("&Close")
        grid.addWidget(self.testImg, 1, 1, 6, 6)
        grid.addWidget(self.closeButton, 7, 7)
        self.setLayout(grid)
        self.closeButton.clicked.connect(self.closeWindow)
        self.show()

    def closeEvent(self, event):
        """
        Closes the window.

        Args:
            event (QEvent): the event of closing the window.

        Returns:
            None.

        """
        self.closeWindow()

    def closeWindow(self):
        """
        Closes the window.

        Returns:
            None

        """
        self.close()


class OriginalScansViewer(QWidget):
    def __init__(self, parent, testNumber, pageData, pages):
        super().__init__()
        self.parent = parent
        self.testNumber = testNumber
        self.numberOfPages = len(pages)
        self.pageList = pages
        # note pagedata  triples [name, image-ref, true/false]
        self.pageNames = [x[0] for x in pageData]
        self.ui = Ui_TestView()
        self.ui.setupUi(self)
        self.connectButtons()
        self.tabs = {}
        self.buildTabs()
        self.setWindowTitle("Original scans of test {}".format(self.testNumber))
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

        self.setMinimumSize(500, 500)

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


class SelectTestQuestion(QDialog):
    def __init__(self, info, gn=None):
        super(SelectTestQuestion, self).__init__()
        self.setModal(True)
        self.setWindowTitle("View another test")
        self.iL = QLabel("From which test do you wish to view the current question?")
        self.ab = QPushButton("&Accept")
        self.ab.clicked.connect(self.accept)
        self.cb = QPushButton("&Cancel")
        self.cb.clicked.connect(self.reject)

        fg = QFormLayout()
        self.tsb = QSpinBox()
        self.tsb.setRange(1, info["numberToProduce"])
        self.tsb.setValue(1)
        fg.addRow("Select test:", self.tsb)
        if gn is not None:
            self.gsb = QSpinBox()
            self.gsb.setRange(1, info["numberOfQuestions"])
            self.gsb.setValue(gn)
            fg.addRow("Select question:", self.gsb)
            self.iL.setText("Which test/group do you wish to view?")
        grid = QGridLayout()
        grid.addWidget(self.iL, 0, 1, 1, 3)
        grid.addLayout(fg, 1, 1, 3, 3)
        grid.addWidget(self.ab, 4, 1)
        grid.addWidget(self.cb, 4, 3)
        self.setLayout(grid)
