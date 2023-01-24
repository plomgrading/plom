# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2021 Forest Kobayashi

import logging

from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
)


log = logging.getLogger("rubric_wrangler")


def showRubricToUser(rubric):
    """Filter the rubrics shown to the user in the wrangler"""
    # hide system rubrics
    if rubric["username"] == "HAL":
        return False
    # hide manager-delta rubrics
    from .rubric_list import rubric_is_naked_delta

    if rubric_is_naked_delta(rubric):
        return False
    # passes filters
    return True


def deltaToInt(x):
    """Since delta can just be a ."""
    if x == ".":
        return 0
    else:
        return int(x)


class DeleteIcon(QPushButton):
    def __init__(self):
        super().__init__()
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
    def __init__(self, data=None):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Display Delta", "Text"])
        if data is not None:
            self._data = data
            self.populate(data)

    def repopulate(self, data):
        self._data = data
        # clear all rows
        self.removeRows(0, self.rowCount())
        self.populate(data)

    def populate(self, data):
        # then repopulate
        for X in data:
            # check if given rubric should appear
            if showRubricToUser(X):
                self.appendRow(
                    [
                        QStandardItem(str(X["id"])),
                        QStandardItem(X["username"]),
                        QStandardItem(str(X["display_delta"])),
                        QStandardItem(X["text"]),
                    ]
                )


class RubricProxyModel(QSortFilterProxyModel):
    def __init__(self, username):
        QSortFilterProxyModel.__init__(self)
        self.username = username
        self.tFilt = ""
        self.uFilt = ""
        self.setDynamicSortFilter(True)
        # Cols = [0"Key", 1"Username", 2"Delta", 3"Text"]

    def setTextFilter(self, txt):
        self.uFilt = ""
        self.tFilt = txt
        self.setFilterKeyColumn(4)

    def setUserFilter(self, txt):
        self.tFilt = ""
        self.uFilt = txt
        self.setFilterKeyColumn(2)

    def filterAcceptsRow(self, pos, index):
        # Cols = [0"Key", 1"Username", 2"Delta", 3"Text"]

        if len(self.tFilt) > 0:  # filter on text
            return (
                self.tFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 3)).casefold()
            )
        elif len(self.uFilt) > 0:  # filter on user
            return (
                self.uFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 1)).casefold()
            )
        else:
            return True

    def lessThan(self, left, right):
        # Cols = [0"Key", 1"Username", 2"Display Delta", 3"Text"]
        # if sorting on key or display_delta then turn things into ints
        if left.column() == 2:  # sort on display_delta - treat '.' as 0
            ld = deltaToInt(self.sourceModel().data(left))
            rd = deltaToInt(self.sourceModel().data(right))
        else:
            ld = self.sourceModel().data(left)
            rd = self.sourceModel().data(right)
        return ld < rd


class ShowTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setStretchLastSection(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Display Delta", "Text"])

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
                log.error(
                    "We have a (minor) problem - trying to populate list with key not in our rubric list."
                )
            else:
                rind = rindices[0]
                # now insert into the table
                rc = self.rowCount()
                # Careful about sorting during setItem calls: Issue #2065
                _sorting_enabled = self.isSortingEnabled()
                self.setSortingEnabled(False)
                self.insertRow(rc)
                self.setItem(rc, 0, QTableWidgetItem(rubrics[rind]["id"]))
                self.setItem(rc, 1, QTableWidgetItem(rubrics[rind]["username"]))
                self.setItem(rc, 2, QTableWidgetItem(rubrics[rind]["display_delta"]))
                self.setItem(rc, 3, QTableWidgetItem(rubrics[rind]["text"]))
                self.setSortingEnabled(_sorting_enabled)

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
        # Careful about sorting during setItem calls: Issue #2065
        _sorting_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
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
            sourceRowCount = len(sourceInd) // 4
            # just before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 0).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [sourceInd[4 * k + j].data() for j in range(4)]
                if rdat[0] in existingKeys:
                    pass
                else:
                    self.insertRow(targetRow)
                    for col in range(4):
                        self.setItem(targetRow, col, QTableWidgetItem(rdat[col]))
                    targetRow += 1
            # # if shift-key pressed - then delete source
            if QApplication.keyboardModifiers() == Qt.ShiftModifier:
                sourceRows = sorted([X.row() for X in sourceInd], reverse=True)
                # is multiple of 4
                for r in sourceRows[0::4]:  # every 4th
                    event.source().removeRow(r)
        else:
            targetRow = self.indexAt(event.pos()).row()
            sourceInd = event.source().selectedIndexes()
            sourceRowCount = len(sourceInd) // 4
            # before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 0).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [sourceInd[4 * k + j].data() for j in range(4)]
                if rdat[0] in existingKeys:
                    pass
                else:
                    self.insertRow(targetRow)
                    for col in range(4):
                        self.setItem(targetRow, col, QTableWidgetItem(rdat[col]))
                    targetRow += 1
        self.setSortingEnabled(_sorting_enabled)


class ShowTabW(QTabWidget):
    def __init__(self, nameList):
        super().__init__()
        self.tabBar().setAcceptDrops(True)
        self.tabBar().setChangeCurrentOnDrag(True)
        for X in nameList:
            self.addTab(ShowTable(), X)

    def dropEvent(self, event):
        self.currentWidget().dropEvent(event)


class DropButton(QPushButton):
    def __init__(self, p, txt):
        super().__init__(txt)
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
        super().__init__()
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
    def __init__(self, parent, rubrics, wranglerState, username, annotator_size=None):
        super().__init__(parent)
        # set size to be 3/4 or parent annotator
        if annotator_size:
            self.resize(annotator_size * 3 / 4)
        ##
        self.username = username
        self.rubrics = rubrics
        self.model = RubricModel()
        self.proxy = RubricProxyModel(username)
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
        self.num_user_tabs = len(wranglerState["user_tabs"])
        tab_names = [x["name"] for x in wranglerState["user_tabs"]]
        tab_names.append("HIDE")
        self.ST = ShowListFrame(tab_names)
        ##
        self.tFiltLE = QLineEdit()
        self.tFiltLE.returnPressed.connect(self.setTextFilter)
        self.uFiltLE = QLineEdit()
        self.uFiltLE.returnPressed.connect(self.setUserFilter)
        ##
        self.aB = QPushButton("&Accept")
        self.aB.clicked.connect(self.returnWrangled)
        self.cB = QPushButton("&Cancel")
        self.cB.clicked.connect(self.reject)
        grid = QGridLayout()
        grid.addWidget(self.rubricTable, 1, 1, 8, 8)
        grid.addWidget(QLabel("Filter on rubric text"), 12, 1, 1, 1)
        grid.addWidget(self.tFiltLE, 12, 2, 1, 2)
        grid.addWidget(QLabel("Filter on rubric username"), 13, 1, 1, 1)
        grid.addWidget(self.uFiltLE, 13, 2, 1, 2)
        grid.addWidget(self.ST, 1, 9, 10, 10)
        grid.addWidget(self.aB, 20, 18)
        grid.addWidget(self.cB, 20, 17)
        self.setLayout(grid)

        # set sensible default state if rubricWidget sends state=none
        if wranglerState is None:
            wranglerState = {
                "shown": [X["id"] for X in self.rubrics],  # all keys
                "hidden": [],
                "tab_order": [],
                "user_tabs": [],
            }
        self.setFromWranglerState(wranglerState)

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
            "tab_order": [],
            "user_tabs": [],
        }
        for p in range(self.num_user_tabs):
            store["user_tabs"].append(
                {
                    "name": self.ST.STW.tabText(p),
                    "ids": self.ST.STW.widget(p).getCurrentKeys(),
                }
            )
        # the hidden tab is stored in the index *after* the last user tab
        store["hidden"] = self.ST.STW.widget(self.num_user_tabs).getCurrentKeys()
        assert self.num_user_tabs + 1 == self.ST.STW.count()
        # anything not hidden is shown
        # columns are ["Key", "Username", "Display Delta", "Text"])
        for r in range(self.model.rowCount()):
            key = self.model.index(r, 0).data()
            # check if is in "hidden" list
            if key in store["hidden"]:
                continue
            # passes all
            store["shown"].append(key)
        return store

    def setFromWranglerState(self, state):
        # does not do any sanity checks
        # set the main list to obey the order in wrangerState, but then append any new rubrics
        rkeys = [X["id"] for X in self.rubrics]  # keys in order
        mainList = []
        # add rubrics in the order from state - which is list of keys
        for key in state["shown"]:
            ind = rkeys.index(key)
            mainList.append(self.rubrics[ind])
        # add any remaining rubrics
        for ind, key in enumerate(rkeys):
            if key not in state["shown"]:
                mainList.append(self.rubrics[ind])
        self.model.repopulate(mainList)
        # populate the ABC lists
        for p in range(self.num_user_tabs):
            self.ST.populate(p, self.rubrics, state["user_tabs"][p]["ids"])
        # populate the hide-list
        idx = self.num_user_tabs
        self.ST.populate(idx, self.rubrics, state["hidden"])

    def returnWrangled(self):
        self.wranglerState = self.toWranglerState()
        self.accept()
