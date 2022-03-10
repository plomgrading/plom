# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from plom.client import ExamView
from plom.client.useful_classes import ErrorMessage


class ActionTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.db = QPushButton("Discard Page")
        self.eb = QPushButton("Extra Page")
        self.tb = QPushButton("Test Page")
        self.hb = QPushButton("Homework Page")
        vb.addWidget(self.eb)
        vb.addWidget(self.tb)
        vb.addWidget(self.hb)
        vb.addWidget(self.db)
        self.setLayout(vb)
        self.db.clicked.connect(self.discard)
        self.hb.clicked.connect(self.homework)
        self.eb.clicked.connect(self.extra)
        self.tb.clicked.connect(self.test)

    def discard(self):
        self._parent.optionTW.setCurrentIndex(4)

    def extra(self):
        self._parent.optionTW.setCurrentIndex(1)

    def test(self):
        self._parent.optionTW.setCurrentIndex(2)

    def homework(self):
        self._parent.optionTW.setCurrentIndex(3)


class DiscardTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        self.db = QPushButton("Click to confirm discard")
        self.ob = QPushButton("Return to other options")
        vb.addStretch(0)
        vb.addWidget(self.db)
        vb.addStretch(0)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.db.clicked.connect(self.discard)
        self.ob.clicked.connect(self.other)

    def discard(self):
        self._parent.action = "discard"
        self._parent.accept()

    def other(self):
        self._parent.optionTW.setCurrentIndex(0)


class ExtraTab(QWidget):
    def __init__(self, parent, maxT, maxQ):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        fl = QFormLayout()
        self.frm = QFrame()
        self.ob = QPushButton("Return to other options")
        self.tsb = QSpinBox()
        self.tsb.setMinimum(1)
        self.tsb.setMaximum(maxT)
        # a group of checkboxes for questions
        # TODO these labels should be from spec
        self.qgb = QGroupBox()
        self.qcbd = {}
        vb2 = QVBoxLayout()
        for q in range(1, maxQ + 1):
            self.qcbd[q] = QCheckBox(f"Q{q}")
            vb2.addWidget(self.qcbd[q])
        self.qgb.setLayout(vb2)
        # put in other widgets
        self.cb = QPushButton("Click to confirm")
        self.vwb = QPushButton("View whole test")
        fl.addRow(QLabel("Test number:"), self.tsb)
        fl.addRow(QLabel("Question numbers:"), self.qgb)
        fl.addRow(self.vwb)
        fl.addRow(self.cb)
        self.frm.setLayout(fl)
        vb.addWidget(self.frm)
        vb.addStretch(1)
        vb.addWidget(self.ob)
        self.setLayout(vb)

        self.vwb.clicked.connect(self.viewWholeTest)
        self.cb.clicked.connect(self.confirm)
        self.ob.clicked.connect(self.other)

    def confirm(self):
        # make sure at least one question is checked
        checked = [q for q in self.qcbd if self.qcbd[q].isChecked()]
        if not checked:
            ErrorMessage("You must select at least one question.").exec_()
            return
        self._parent.action = "extra"
        self._parent.test = self.tsb.value()
        # store list of questions as comma-delimited string
        self._parent.pq = ",".join([str(q) for q in checked])
        self._parent.accept()

    def viewWholeTest(self):
        self._parent.viewWholeTest(self.tsb.value())

    def other(self):
        self._parent.optionTW.setCurrentIndex(0)


class HWTab(QWidget):
    def __init__(self, parent, maxQ, iDict):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        fl = QFormLayout()
        self.frm = QFrame()
        self.ob = QPushButton("Return to other options")
        self.sidle = QLineEdit()
        # set up sid completion
        self.sidTestDict = {"{}: {}".format(iDict[x][0], iDict[x][1]): x for x in iDict}
        self.sidlist = QStringListModel()
        self.sidlist.setStringList([x for x in self.sidTestDict])
        self.sidcompleter = QCompleter()
        self.sidcompleter.setCaseSensitivity(Qt.CaseInsensitive)
        self.sidcompleter.setFilterMode(Qt.MatchContains)
        self.sidcompleter.setModel(self.sidlist)
        self.sidle.setCompleter(self.sidcompleter)
        # a group of checkboxes for questions
        # TODO these labels should be from spec
        self.qgb = QGroupBox()
        self.qcbd = {}
        vb2 = QVBoxLayout()
        for q in range(1, maxQ + 1):
            self.qcbd[q] = QCheckBox(f"Q{q}")
            vb2.addWidget(self.qcbd[q])
        self.qgb.setLayout(vb2)
        # now set up other gui elements
        self.testl = QLabel("")
        self.cb = QPushButton("Click to confirm")
        self.vwb = QPushButton("View whole test")
        fl.addRow(QLabel("Student ID / Name:"))
        fl.addRow(self.sidle)
        fl.addRow(QLabel("Test number:"), self.testl)
        fl.addRow(QLabel("Question numbers:"), self.qgb)
        fl.addRow(self.vwb)
        fl.addRow(self.cb)
        self.frm.setLayout(fl)
        vb.addWidget(self.frm)
        vb.addStretch(1)
        vb.addWidget(self.ob)
        self.setLayout(vb)
        self.vwb.clicked.connect(self.viewWholeTest)
        self.cb.clicked.connect(self.confirm)
        self.ob.clicked.connect(self.other)
        self.sidle.returnPressed.connect(self.checkID)
        # check ID when user clicks on entry in completer pop-up - not just when return pressed
        self.sidcompleter.activated.connect(self.checkID)

    def checkID(self):
        sid = self.sidle.text()
        if sid in self.sidTestDict:
            self.testl.setText(self.sidTestDict[sid])
        else:
            self.testl.setText("")

    def confirm(self):
        if self.testl.text() == "":
            return
        # make sure at least one question is checked
        checked = [q for q in self.qcbd if self.qcbd[q].isChecked()]
        if not checked:
            ErrorMessage("You must select at least one question.").exec_()
            return
        self._parent.action = "homework"
        self._parent.sid = self.sidle.text()
        # store list of questions as comma-delimited string
        self._parent.pq = ",".join([str(q) for q in checked])
        self._parent.test = int(self.testl.text())
        self._parent.accept()

    def viewWholeTest(self):
        if self.testl.text() == "":
            return
        else:
            self._parent.viewWholeTest(int(self.testl.text()))

    def other(self):
        self._parent.optionTW.setCurrentIndex(0)


class TestTab(QWidget):
    def __init__(self, parent, maxT, maxP):
        super().__init__(parent)
        self._parent = parent
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
        self.cpb.clicked.connect(self.checkTPage)
        self.vwb.clicked.connect(self.viewWholeTest)
        self.cb.clicked.connect(self.confirm)
        self.ob.clicked.connect(self.other)

    def confirm(self):
        self._parent.action = "test"
        self._parent.test = self.tsb.value()
        self._parent.pq = f"{self.psb.value()}"
        self._parent.accept()

    def checkTPage(self):
        self._parent.checkTPage(self.tsb.value(), self.psb.value())

    def viewWholeTest(self):
        self._parent.viewWholeTest(self.tsb.value())

    def other(self):
        self._parent.optionTW.setCurrentIndex(0)


class UnknownViewWindow(QDialog):
    """Simple view window for pageimages"""

    def __init__(self, parent, fnames, tpq, iDict):
        super().__init__(parent)
        self.numberOfTests = tpq[0]
        self.numberOfPages = tpq[1]
        self.numberOfQuestions = tpq[2]
        self.iDict = iDict

        self.action = ""
        self.test = 0
        self.pq = ""
        self.sid = ""

        self.view = ExamView(fnames, dark_background=True)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.optionTW = QTabWidget()

        # reset view button passes to the UnknownView.
        self.resetB = QPushButton("reset view")
        self.rotatePlusB = QPushButton("rotate +90")
        self.rotateMinusB = QPushButton("rotate -90")
        self.cancelB = QPushButton("&cancel")

        self.cancelB.clicked.connect(self.reject)
        self.resetB.clicked.connect(lambda: self.view.resetView())
        self.rotatePlusB.clicked.connect(self.rotatePlus)
        self.rotateMinusB.clicked.connect(self.rotateMinus)

        self.resetB.setAutoDefault(False)  # return won't click the button by default.
        self.rotatePlusB.setAutoDefault(False)
        self.rotateMinusB.setAutoDefault(False)

        # Layout simply
        grid = QGridLayout()
        grid.addWidget(self.view, 1, 1, 10, 10)
        grid.addWidget(self.optionTW, 1, 11, 10, -1)
        grid.addWidget(self.resetB, 11, 1)
        grid.addWidget(self.rotatePlusB, 11, 2)
        grid.addWidget(self.rotateMinusB, 11, 3)
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
        t1 = ExtraTab(self, self.numberOfTests, self.numberOfQuestions)
        t2 = TestTab(self, self.numberOfTests, self.numberOfPages)
        t3 = HWTab(self, self.numberOfQuestions, self.iDict)
        t4 = DiscardTab(self)
        self.optionTW.addTab(t0, "Actions")
        self.optionTW.addTab(t1, "Extra Page")
        self.optionTW.addTab(t2, "Test Page")
        self.optionTW.addTab(t3, "Homework Page")
        self.optionTW.addTab(t4, "Discard")

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

    def viewQuestion(self, testNumber, questionNumber):
        self.parent().viewQuestion(testNumber, questionNumber, parent=self)

    def viewWholeTest(self, testNumber):
        self.parent().viewWholeTest(testNumber, parent=self)

    def checkTPage(self, testNumber, pageNumber):
        self.parent().checkTPage(testNumber, pageNumber, parent=self)
