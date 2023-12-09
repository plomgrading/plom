# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from plom.client import ImageViewWidget
from plom.client.useful_classes import WarnMsg


class DiscardTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        vb = QVBoxLayout()
        db = QPushButton("Click to co&nfirm discard")
        vb.addStretch(0)
        vb.addWidget(db)
        vb.addStretch(0)
        self.setLayout(vb)
        db.clicked.connect(self.discard)

    def discard(self):
        self._parent.action = "discard"
        self._parent.accept()


class ExtraTab(QWidget):
    def __init__(self, parent, max_paper_num, questionLabels):
        super().__init__(parent)
        self._parent = parent
        fl = QFormLayout()
        self.tsb = QSpinBox()
        self.tsb.setRange(1, max_paper_num)
        # Initially blank for Issue #3127, but careful the default is still 1
        self.tsb.clear()
        qgb = QGroupBox("&Assign to questions:")
        self.questionCheckBoxes = [QCheckBox(x) for x in questionLabels]
        vb = QVBoxLayout()
        for x in self.questionCheckBoxes:
            vb.addWidget(x)
        qgb.setLayout(vb)
        # put in other widgets
        cb = QPushButton("Click to co&nfirm")
        vwb = QPushButton("&View whole test")
        fl.addRow("Test number:", self.tsb)
        fl.addRow(qgb)
        fl.addRow(vwb)
        fl.addRow(cb)
        self.setLayout(fl)
        vwb.clicked.connect(self.viewWholeTest)
        cb.clicked.connect(self.confirm)

    def confirm(self):
        if not self.tsb.text():
            WarnMsg(self, "You must choose a paper number.").exec()
            return
        checked = [i for i, x in enumerate(self.questionCheckBoxes) if x.isChecked()]
        if not checked:
            WarnMsg(self, "You must select at least one question.").exec()
            return
        self._parent.action = "extra"
        self._parent.test = self.tsb.value()
        # store list of questions as comma-delimited string, 1-based indexing
        self._parent.pq = ",".join([str(i + 1) for i in checked])
        self._parent.accept()

    def viewWholeTest(self):
        self._parent.viewWholeTest(self.tsb.value())


class HWTab(QWidget):
    def __init__(self, parent, questionLabels, iDict):
        super().__init__(parent)
        self._parent = parent
        fl = QFormLayout()
        self.sidle = QLineEdit()
        # set up sid completion
        self.sidTestDict = {"{}: {}".format(iDict[x][0], iDict[x][1]): x for x in iDict}
        self.sidlist = QStringListModel()
        self.sidlist.setStringList([x for x in self.sidTestDict])
        self.sidcompleter = QCompleter()
        self.sidcompleter.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.sidcompleter.setFilterMode(Qt.MatchFlag.MatchContains)
        self.sidcompleter.setModel(self.sidlist)
        self.sidle.setCompleter(self.sidcompleter)
        qgb = QGroupBox("&Assign to questions:")
        self.questionCheckBoxes = [QCheckBox(x) for x in questionLabels]
        vb = QVBoxLayout()
        for x in self.questionCheckBoxes:
            vb.addWidget(x)
        qgb.setLayout(vb)
        # now set up other gui elements
        self.testl = QLabel("")
        cb = QPushButton("Click to co&nfirm")
        vwb = QPushButton("&View whole test")
        fl.addRow(QLabel("Student ID / Name:"))
        fl.addRow(self.sidle)
        fl.addRow("Test number:", self.testl)
        fl.addRow(qgb)
        fl.addRow(vwb)
        fl.addRow(cb)
        self.setLayout(fl)
        vwb.clicked.connect(self.viewWholeTest)
        cb.clicked.connect(self.confirm)
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
        checked = [i for i, x in enumerate(self.questionCheckBoxes) if x.isChecked()]
        if not checked:
            WarnMsg(self, "You must select at least one question.").exec()
            return
        self._parent.action = "homework"
        self._parent.sid = self.sidle.text()
        # store list of questions as comma-delimited string, 1-based indexing
        self._parent.pq = ",".join([str(i + 1) for i in checked])
        self._parent.test = int(self.testl.text())
        self._parent.accept()

    def viewWholeTest(self):
        if self.testl.text() == "":
            return
        else:
            self._parent.viewWholeTest(int(self.testl.text()))


class TestTab(QWidget):
    def __init__(self, parent, max_paper_num, max_page_num):
        super().__init__(parent)
        self._parent = parent
        fl = QFormLayout()
        self.tsb = QSpinBox()
        self.psb = QSpinBox()
        self.tsb.setRange(1, max_paper_num)
        self.psb.setRange(1, max_page_num)
        # Initially blank for Issue #3127
        self.tsb.clear()
        self.psb.clear()
        cb = QPushButton("Click to co&nfirm")
        cpb = QPushButton("Check that page")
        vwb = QPushButton("&View whole test")
        fl.addRow("Test number:", self.tsb)
        fl.addRow("Page number:", self.psb)
        fl.addRow(cpb)
        fl.addRow(vwb)
        fl.addRow(cb)
        self.setLayout(fl)
        cpb.clicked.connect(self.checkTPage)
        vwb.clicked.connect(self.viewWholeTest)
        cb.clicked.connect(self.confirm)

    def confirm(self):
        if not self.tsb.text():
            WarnMsg(self, "You must choose a paper number.").exec()
            return
        if not self.psb.text():
            WarnMsg(self, "You must choose a page number.").exec()
            return
        self._parent.action = "test"
        self._parent.test = self.tsb.value()
        self._parent.pq = f"{self.psb.value()}"
        self._parent.accept()

    def checkTPage(self):
        self._parent.checkTPage(self.tsb.value(), self.psb.value())

    def viewWholeTest(self):
        self._parent.viewWholeTest(self.tsb.value())


class UnknownViewWindow(QDialog):
    """Simple view window for pageimages."""

    def __init__(self, parent, fnames, stuff, iDict):
        super().__init__(parent)
        self.numberOfTests = stuff[0]
        self.numberOfPages = stuff[1]
        self.questionLabels = stuff[2]
        self.iDict = iDict

        if len(fnames) > 1:
            self.setWindowTitle("Multiple unknown pages")
        else:
            (p,) = fnames
            self.setWindowTitle(
                f"Unknown {p['pagename']}: p. {p['bundle_position']} of bundle {p['bundle_name']}"
            )
        self.action = ""
        self.test = 0
        self.pq = ""
        self.sid = ""

        self.img = ImageViewWidget(self, fnames, dark_background=True)
        self.optionTW = QTabWidget()
        self.optionTW.setTabPosition(QTabWidget.TabPosition.East)

        cancelB = QPushButton("&Cancel")
        cancelB.clicked.connect(self.reject)

        grid = QHBoxLayout()
        grid.addWidget(self.img)
        vb = QVBoxLayout()
        vb.addWidget(self.optionTW)
        hb = QHBoxLayout()
        hb.addStretch(1)
        hb.addWidget(cancelB)
        vb.addLayout(hb)
        grid.addLayout(vb)
        self.setLayout(grid)

        t1 = ExtraTab(self, self.numberOfTests, self.questionLabels)
        t2 = TestTab(self, self.numberOfTests, self.numberOfPages)
        t3 = HWTab(self, self.questionLabels, self.iDict)
        t4 = DiscardTab(self)
        self.optionTW.addTab(t1, "&Extra Page")
        self.optionTW.addTab(t2, "&Test Page")
        self.optionTW.addTab(t3, "&Homework Page")
        self.optionTW.addTab(t4, "&Discard")

        # hack/workaround: keep focus away from left-hand panel: Issue #2271
        t1.setFocus()

    def get_orientation(self):
        return self.img.get_orientation()

    def viewWholeTest(self, testNumber):
        self.parent().viewWholeTest(testNumber, parent=self)

    def checkTPage(self, testNumber, pageNumber):
        self.parent().checkTPage(testNumber, pageNumber, parent=self)
