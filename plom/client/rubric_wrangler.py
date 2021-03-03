# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


def deltaToInt(x):
    """Since delta can just be a . """
    if x == ".":
        return 0
    else:
        return int(x)


class DeleteIcon(QPushButton):
    def __init__(self):
        super(DeleteIcon, self).__init__()
        self.setText("Drag here\n to remove\n from tab")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def dragEnterEvent(self, e):
        if isinstance(e.source(), ShowTable):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        sourceRow = e.source().selectedIndexes()[0].row()
        e.source().removeRow(sourceRow)
        e.accept()


class RubricModel(QStandardItemModel):
    def __init__(self, data):
        super(RubricModel, self).__init__()
        self._data = data
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Key", "Question", "Username", "Delta", "Text"])
        self.populate(data)

    def populate(self, data, hideHAL=True):
        # clear all rows
        self.removeRows(0, self.rowCount())
        # then repopulate
        for X in data:
            # hide HAL generated rubrics
            if hideHAL and X["username"] == "HAL":
                continue
            self.appendRow(
                [
                    QStandardItem(str(X["id"])),
                    QStandardItem(str(X["question_number"])),
                    QStandardItem(X["username"]),
                    QStandardItem(str(X["delta"])),
                    QStandardItem(X["text"]),
                ]
            )


class RubricProxyModel(QSortFilterProxyModel):
    def __init__(self, username, question_number):
        QSortFilterProxyModel.__init__(self)
        self.username = username
        self.question_number = str(question_number)
        self.tFilt = ""
        self.uFilt = ""
        self.hideQ = Qt.Checked
        self.hideU = Qt.Unchecked
        self.hideM = Qt.Unchecked
        self.setDynamicSortFilter(True)
        # Cols = [0"Key", 1"Question", 2"Username", 3"Delta", 4"Text"]

    def setBinaryFilters(self, hideQ, hideU, hideM):
        self.hideQ = hideQ
        self.hideU = hideU
        self.hideM = hideM
        self.setFilterKeyColumn(2)  # to trigger a refresh

    def setTextFilter(self, txt):
        self.uFilt = ""
        self.tFilt = txt
        self.setFilterKeyColumn(4)

    def setUserFilter(self, txt):
        self.tFilt = ""
        self.uFilt = txt
        self.setFilterKeyColumn(2)

    def filterAcceptsRow(self, pos, index):
        # Cols = [0"Key", 1"Question", 2"Username", 3"Delta", 4"Text"]
        # check question number hiding
        if self.hideQ == Qt.Checked and (
            self.sourceModel().data(self.sourceModel().index(pos, 1))
            != self.question_number
        ):
            return False
        # check username number hiding (except manager)
        if self.hideU == Qt.Checked and (
            self.sourceModel().data(self.sourceModel().index(pos, 2))
            not in [self.username, "manager"]
        ):
            return False
        # check manager hiding
        if self.hideM == Qt.Checked and (
            self.sourceModel().data(self.sourceModel().index(pos, 2)) == "manager"
        ):
            return False

        if len(self.tFilt) > 0:  # filter on text
            return (
                self.tFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
            )
        elif len(self.uFilt) > 0:  # filter on user
            return (
                self.uFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 2)).casefold()
            )
        else:
            return True

    def lessThan(self, left, right):
        # Cols = [0"Key", 1"Question", 2"Username", 3"Delta", 4"Text"]
        # if sorting on key or delta then turn things into ints
        if left.column() == 3:  # sort on delta - treat '.' as 0
            ld = deltaToInt(self.sourceModel().data(left))
            rd = deltaToInt(self.sourceModel().data(right))
        else:
            ld = self.sourceModel().data(left)
            rd = self.sourceModel().data(right)
        return ld < rd


class ShowTable(QTableWidget):
    def __init__(self):
        super(ShowTable, self).__init__()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Key", "Question", "Username", "Delta", "Text"])

    def cleanUp(self):
        # remove all rows
        for r in range(self.rowCount()):
            self.removeRow(0)

    def populate(self, rubrics, keys):
        # insert in key order
        for k in keys:
            # find the rubric with that key
            rindices = [i for i, v in enumerate(rubrics) if int(v["id"]) == int(k)]
            if len(rindices) != 1:
                print(
                    "We have a (minor) problem - trying to populate list with key not in our rubric list."
                )
            else:
                rind = rindices[0]
                # now insert into the table
                rc = self.rowCount()
                self.insertRow(rc)
                self.setItem(rc, 0, QTableWidgetItem(rubrics[rind]["id"]))
                self.setItem(rc, 1, QTableWidgetItem(rubrics[rind]["question_number"]))
                self.setItem(rc, 2, QTableWidgetItem(rubrics[rind]["username"]))
                self.setItem(rc, 3, QTableWidgetItem(rubrics[rind]["delta"]))
                self.setItem(rc, 4, QTableWidgetItem(rubrics[rind]["text"]))

    def getCurrentKeys(self):
        current_keys = []
        for r in range(self.rowCount()):
            current_keys.append(self.item(r, 0).text())
        return current_keys

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            row = self.currentRow()
            self.removeRow(row)
        else:
            super().keyPressEvent(event)

    def dropMimeData(self, r, c, dat, act):
        # always drop at column 0
        return super().dropMimeData(r, 0, dat, act)

    def dropEvent(self, event):
        # fixed drop event using
        # https://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget
        if event.source() == self:
            event.setDropAction(Qt.CopyAction)
            rows = set([mi.row() for mi in self.selectedIndexes()])
            targetRow = self.indexAt(event.pos()).row()
            rows.discard(targetRow)
            rows = sorted(rows)
            if not rows:
                return
            if targetRow == -1:
                targetRow = self.rowCount()
            for _ in range(len(rows)):
                self.insertRow(targetRow)
            rowMapping = dict()  # Src row to target row.
            for idx, row in enumerate(rows):
                if row < targetRow:
                    rowMapping[row] = targetRow + idx
                else:
                    rowMapping[row + len(rows)] = targetRow + idx
            colCount = self.columnCount()
            for srcRow, tgtRow in sorted(rowMapping.items()):
                for col in range(0, colCount):
                    self.setItem(tgtRow, col, self.takeItem(srcRow, col))
            for row in reversed(sorted(list(rowMapping.keys()))):
                self.removeRow(row)
            event.accept()
        elif isinstance(event.source(), ShowTable):  # move between lists
            targetRow = self.indexAt(event.pos()).row()
            sourceInd = event.source().selectedIndexes()
            sourceRowCount = len(sourceInd) // 5
            # just before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 0).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [sourceInd[5 * k + j].data() for j in range(5)]
                if rdat[1] in existingKeys:
                    pass
                else:
                    self.insertRow(targetRow)
                    for col in range(5):
                        self.setItem(targetRow, col, QTableWidgetItem(rdat[col]))
                    targetRow += 1
            # # if shift-key pressed - then delete source
            if QApplication.keyboardModifiers() == Qt.ShiftModifier:
                sourceRows = sorted([X.row() for X in sourceInd], reverse=True)
                # is multiple of 5
                for r in sourceRows[0::5]:  # every th
                    event.source().removeRow(r)
        else:
            targetRow = self.indexAt(event.pos()).row()
            sourceInd = event.source().selectedIndexes()
            sourceRowCount = len(sourceInd) // 5
            # before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 0).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [sourceInd[5 * k + j].data() for j in range(5)]
                if rdat[1] in existingKeys:
                    pass
                else:
                    self.insertRow(targetRow)
                    for col in range(5):
                        self.setItem(targetRow, col, QTableWidgetItem(rdat[col]))
                    targetRow += 1


class ShowTabW(QTabWidget):
    def __init__(self, nameList):
        super(ShowTabW, self).__init__()
        self.tabBar().setAcceptDrops(True)
        self.tabBar().setChangeCurrentOnDrag(True)
        for X in nameList:
            self.addTab(ShowTable(), X)

    def addTab(self, widget, text):
        p = super().addTab(widget, text)

    def dropEvent(self, event):
        self.currentWidget().dropEvent(event)


class DropButton(QPushButton):
    def __init__(self, p, txt):
        super(DropButton, self).__init__(txt)
        self.setAcceptDrops(True)
        self.index = p
        self.clicked.connect(self.payAttentionToMe)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def payAttentionToMe(self):
        self.setFocus(Qt.TabFocusReason)
        self.parent().setCurrentIndex(self.index)

    def dragEnterEvent(self, e):
        if isinstance(e.source(), QTableView):
            # self.payAttentionToMe()
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event):
        self.payAttentionToMe()
        self.parent().STW.dropEvent(event)
        super().dropEvent(event)


class ShowListFrame(QFrame):
    def __init__(self, nameList):
        super(ShowListFrame, self).__init__()
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.STW = ShowTabW(nameList)
        self.DI = DeleteIcon()
        vl = QVBoxLayout()
        for n, X in enumerate(nameList):
            vl.addWidget(DropButton(n, X))
        hl = QHBoxLayout()
        hl.addLayout(vl)
        ##
        hl.addWidget(self.STW)
        hl.addWidget(self.DI)
        self.setLayout(hl)

    def setCurrentIndex(self, index):
        self.STW.setCurrentIndex(index)

    def populate(self, p, rubrics, keys):
        self.STW.widget(p).cleanUp()
        self.STW.widget(p).populate(rubrics, keys)


class RubricWrangler(QDialog):
    def __init__(self, rubrics, wranglerState, username, question_number):
        super(RubricWrangler, self).__init__()
        self.resize(1200, 768)
        self.username = username
        self.question_number = question_number
        self.rubrics = rubrics
        self.model = RubricModel(rubrics)
        self.proxy = RubricProxyModel(username, question_number)
        self.rubricTable = QTableView()
        self.proxy.setSourceModel(self.model)
        self.rubricTable.setModel(self.proxy)
        self.rubricTable.sortByColumn(-1, Qt.AscendingOrder)
        self.rubricTable.verticalHeader().setVisible(False)
        self.rubricTable.horizontalHeader().setVisible(True)
        self.rubricTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rubricTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rubricTable.resizeColumnsToContents()
        self.rubricTable.horizontalHeader().setStretchLastSection(True)
        self.rubricTable.setSortingEnabled(True)
        self.rubricTable.setDragEnabled(True)
        self.rubricTable.setAcceptDrops(False)
        ##
        self.ST = ShowListFrame(["List A", "List B", "List C", "HIDE"])
        ##
        self.tFiltLE = QLineEdit()
        self.tFiltLE.returnPressed.connect(self.setTextFilter)
        self.uFiltLE = QLineEdit()
        self.uFiltLE.returnPressed.connect(self.setUserFilter)
        ##
        self.cbQ = QCheckBox("Hide comments from other questions **recommended**")
        self.cbU = QCheckBox("Hide comments from other users (except manager)")
        self.cbM = QCheckBox("Hide comments from manager")
        # connect checkboxes to filters
        self.cbQ.stateChanged.connect(self.setCheckBoxFilters)
        self.cbU.stateChanged.connect(self.setCheckBoxFilters)
        self.cbM.stateChanged.connect(self.setCheckBoxFilters)
        ##
        self.aB = QPushButton("&Accept")
        self.aB.clicked.connect(self.returnWrangled)
        self.cB = QPushButton("&Cancel")
        self.cB.clicked.connect(self.reject)
        grid = QGridLayout()
        grid.addWidget(self.rubricTable, 4, 1, 8, 8)
        grid.addWidget(self.cbQ, 1, 1, 1, 2)
        grid.addWidget(self.cbU, 2, 1, 1, 2)
        grid.addWidget(self.cbM, 3, 1, 1, 2)
        grid.addWidget(QLabel("Filter on rubric text"), 10, 9, 1, 1)
        grid.addWidget(self.tFiltLE, 10, 10, 1, 2)
        grid.addWidget(QLabel("Filter on rubric username"), 11, 9, 1, 1)
        grid.addWidget(self.uFiltLE, 11, 10, 1, 2)
        grid.addWidget(self.ST, 1, 9, 8, 8)
        grid.addWidget(self.aB, 20, 20)
        grid.addWidget(self.cB, 20, 19)
        self.setLayout(grid)

        # set sensible default state if rubricWidget sends state=none
        if wranglerState is None:
            self.wranglerState = {
                "shown": [],
                "hidden": [],
                "tabs": [[], [], []],
                "hideManager": Qt.Unchecked,
                "hideUsers": Qt.Unchecked,
                "hideQuestions": Qt.Checked,
            }
        else:
            self.wranglerState = wranglerState
        # use this to set state
        self.setFromWranglerState()

    def setCheckBoxes(self):
        self.cbQ.setCheckState(Qt.Checked if self.curFilters[0] else Qt.Unchecked)
        self.cbU.setCheckState(Qt.Checked if self.curFilters[1] else Qt.Unchecked)
        self.cbM.setCheckState(Qt.Checked if self.curFilters[2] else Qt.Unchecked)
        ##

    def setCheckBoxFilters(self):
        self.proxy.setBinaryFilters(
            self.cbQ.checkState(),
            self.cbU.checkState(),
            self.cbM.checkState(),
        )

    def setTextFilter(self):
        self.proxy.setTextFilter(self.tFiltLE.text())
        self.uFiltLE.clear()

    def setUserFilter(self):
        self.proxy.setUserFilter(self.uFiltLE.text())
        self.tFiltLE.clear()

    def toWranglerState(self):
        store = {
            "shown": [],
            "hidden": [],
            "tabs": [],
            "hideManager": self.cbM.checkState(),
            "hideUsers": self.cbU.checkState(),
            "hideQuestions": self.cbQ.checkState(),
        }
        # get listsA,B,C from first 3 tabs
        for p in range(3):
            store["tabs"].append(self.ST.STW.widget(p).getCurrentKeys())
        # get hidden from widget3 = hidelist
        store["hidden"] = self.ST.STW.widget(3).getCurrentKeys()
        # anything not hidden is shown
        for r in range(self.model.rowCount()):
            key = self.model.index(r, 0).data()
            # check against various filters
            if key in store["hidden"]:
                continue
            # columns are ["Key", "Question", "Username", "Delta", "Text"])
            # check question number filtering - col1
            if self.cbQ.checkState() == Qt.Checked and self.model.index(
                r, 1
            ).data() != str(self.question_number):
                continue
            # check username filtering - col2
            if self.cbU.checkState() == Qt.Checked and self.model.index(
                r, 2
            ).data() not in [
                self.username,
                "manager",
            ]:
                continue
            # check manager filtering
            if (
                self.cbM.checkState() == Qt.Checked
                and self.model.index(r, 2).data() == "manager"
            ):
                continue
            # passes all
            store["shown"].append(key)
        return store

    def setFromWranglerState(self):
        # does not do any sanity checks
        # set the checkboxes
        self.cbQ.setCheckState(self.wranglerState["hideQuestions"])
        self.cbU.setCheckState(self.wranglerState["hideUsers"])
        self.cbM.setCheckState(self.wranglerState["hideManager"])
        # main list already populated from rubrics on init
        # self.model.populate(self.rubrics)
        # populate the ABC lists
        for p in range(3):
            self.ST.populate(p, self.rubrics, self.wranglerState["tabs"][p])
        # populate the hide-list
        self.ST.populate(3, self.rubrics, self.wranglerState["hidden"])

    def returnWrangled(self):
        self.wranglerState = self.toWranglerState()
        self.accept()
