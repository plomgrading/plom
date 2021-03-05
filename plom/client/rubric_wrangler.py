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


def showRubricToUser(rubric):
    """Filter the rubrics shown to the user in the wrangler"""
    # hide system rubrics
    if rubric["username"] == "HAL":
        return False
    # hide manager-delta rubrics
    print("U{}M{}".format(rubric["username"], rubric["meta"]))
    if rubric["username"] == "manager" and rubric["meta"] == "delta":
        return False
    # passes filters
    return True


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
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Delta", "Text"])
        self.populate(data)

    def populate(self, data):
        # clear all rows
        self.removeRows(0, self.rowCount())
        # then repopulate
        for X in data:
            # check if given rubric should appear
            if showRubricToUser(X):
                self.appendRow(
                    [
                        QStandardItem(str(X["id"])),
                        QStandardItem(X["username"]),
                        QStandardItem(str(X["delta"])),
                        QStandardItem(X["text"]),
                    ]
                )


class RubricProxyModel(QSortFilterProxyModel):
    def __init__(self, username):
        QSortFilterProxyModel.__init__(self)
        self.username = username
        self.tFilt = ""
        self.uFilt = ""
        self.hideU = Qt.Unchecked
        self.hideM = Qt.Unchecked
        self.setDynamicSortFilter(True)
        # Cols = [0"Key", 1"Username", 2"Delta", 3"Text"]

    def setBinaryFilters(self, hideU, hideM):
        self.hideU = hideU
        self.hideM = hideM
        self.setFilterKeyColumn(1)  # to trigger a refresh

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
        # check username number hiding (except manager)
        if self.hideU == Qt.Checked and (
            self.sourceModel().data(self.sourceModel().index(pos, 1))
            not in [self.username, "manager"]
        ):
            return False
        # check manager hiding
        if self.hideM == Qt.Checked and (
            self.sourceModel().data(self.sourceModel().index(pos, 1)) == "manager"
        ):
            return False

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
        # Cols = [0"Key", 1"Username", 2"Delta", 3"Text"]
        # if sorting on key or delta then turn things into ints
        if left.column() == 2:  # sort on delta - treat '.' as 0
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
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Key", "Username", "Delta", "Text"])

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
                self.setItem(rc, 1, QTableWidgetItem(rubrics[rind]["username"]))
                self.setItem(rc, 2, QTableWidgetItem(rubrics[rind]["delta"]))
                self.setItem(rc, 3, QTableWidgetItem(rubrics[rind]["text"]))

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
    def __init__(self, rubrics, wranglerState, username):
        super(RubricWrangler, self).__init__()
        self.resize(1200, 768)
        self.username = username
        self.rubrics = rubrics
        self.model = RubricModel(rubrics)
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
        self.ST = ShowListFrame(["List A", "List B", "List C", "HIDE"])
        ##
        self.tFiltLE = QLineEdit()
        self.tFiltLE.returnPressed.connect(self.setTextFilter)
        self.uFiltLE = QLineEdit()
        self.uFiltLE.returnPressed.connect(self.setUserFilter)
        ##
        self.cbU = QCheckBox("Hide comments from other users (except manager)")
        self.cbM = QCheckBox("Hide comments from manager")
        # connect checkboxes to filters
        self.cbU.stateChanged.connect(self.setCheckBoxFilters)
        self.cbM.stateChanged.connect(self.setCheckBoxFilters)
        ##
        self.aB = QPushButton("&Accept")
        self.aB.clicked.connect(self.returnWrangled)
        self.cB = QPushButton("&Cancel")
        self.cB.clicked.connect(self.reject)
        grid = QGridLayout()
        grid.addWidget(self.rubricTable, 3, 1, 8, 8)
        grid.addWidget(self.cbU, 1, 1, 1, 2)
        grid.addWidget(self.cbM, 2, 1, 1, 2)
        grid.addWidget(QLabel("Filter on rubric text"), 12, 1, 1, 1)
        grid.addWidget(self.tFiltLE, 12, 2, 1, 2)
        grid.addWidget(QLabel("Filter on rubric username"), 13, 1, 1, 1)
        grid.addWidget(self.uFiltLE, 13, 2, 1, 2)
        grid.addWidget(self.ST, 1, 9, 10, 10)
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
            }
        else:
            self.wranglerState = wranglerState
        # use this to set state
        self.setFromWranglerState()

    def setCheckBoxFilters(self):
        self.proxy.setBinaryFilters(
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
            # columns are ["Key", "Username", "Delta", "Text"])
            # check question number filtering - col1
            # check username filtering - col1
            if self.cbU.checkState() == Qt.Checked and self.model.index(
                r, 1
            ).data() not in [
                self.username,
                "manager",
            ]:
                continue
            # check manager filtering
            if (
                self.cbM.checkState() == Qt.Checked
                and self.model.index(r, 1).data() == "manager"
            ):
                continue
            # passes all
            store["shown"].append(key)
        return store

    def setFromWranglerState(self):
        # does not do any sanity checks
        # set the checkboxes
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
