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
        self.setHorizontalHeaderLabels(["Shown", "Key", "Username", "Delta", "Text"])
        self.populate(data)

    def populate(self, data):
        self.removeRows(0, self.rowCount())
        for X in data:
            showCheck = QStandardItem(" ")
            showCheck.setCheckable(True)
            showCheck.setCheckState(Qt.Checked)
            self.appendRow(
                [
                    showCheck,
                    QStandardItem(str(X["id"])),
                    QStandardItem(X["username"]),
                    QStandardItem(str(X["delta"])),
                    QStandardItem(X["text"]),
                ]
            )

    def setHideList(self, hideList):
        for r in self.rowCount():
            if self.item(r, 1).text() in hideList:
                self.item(r, 0).setCheckState(Qt.Unchecked)
            else:
                self.item(r, 0).setCheckState(Qt.Checked)


class RubricProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.tFilt = ""
        self.uFilt = ""

    def setTextFilter(self, txt):
        self.uFilt = ""
        self.tFilt = txt
        self.setFilterKeyColumn(4)

    def setUserFilter(self, txt):
        self.tFilt = ""
        self.uFilt = txt
        self.setFilterKeyColumn(2)

    def filterAcceptsRow(self, pos, index):
        if len(self.tFilt) > 0:  # filter on text
            return (
                self.tFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
            )
        elif len(self.uFilt) > 0:  # filter on text
            return (
                self.uFilt.casefold()
                in self.sourceModel().data(self.sourceModel().index(pos, 2)).casefold()
            )
        else:
            return True

    def lessThan(self, left, right):
        # if sorting on key or delta then turn things into ints
        if left.column() == 3:
            ld = int(self.sourceModel().data(left))
            rd = int(self.sourceModel().data(right))
        if left.column() == 1:
            ld = self.sourceModel().item(left.row(), left.column()).checkState()
            rd = self.sourceModel().item(right.row(), right.column()).checkState()
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
        self.setHorizontalHeaderLabels(["Shown", "Key", "Username", "Delta", "Text"])
        self.hideColumn(0)

    def cleanUp(self):
        for r in range(self.rowCount()):
            self.removeRow(0)

    def populate(self, rubrics, keys):
        for k in keys:
            rk = [i for i, v in enumerate(rubrics) if int(v[0]) == int(k)]
            if len(rk) != 1:
                print("We have a problem")
            else:
                rc = self.rowCount()
                self.insertRow(rc)
                self.setItem(rc, 0, QTableWidgetItem(""))
                for c in range(4):
                    self.setItem(rc, c + 1, QTableWidgetItem("{}".format(rubrics[rk])))

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
            sourceRowCount = len(sourceInd) // 4  # 0th col is hidden
            # before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 1).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [""] + [sourceInd[4 * k + j].data() for j in range(4)]
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
                # is multiple of 4
                for r in sourceRows[0::4]:  # every 4th
                    print("Removing row ", r)
                    event.source().removeRow(r)
        else:
            targetRow = self.indexAt(event.pos()).row()
            sourceInd = event.source().selectedIndexes()
            sourceRowCount = len(sourceInd) // 5
            # before you drop - make a list of keys already in table
            existingKeys = [self.item(k, 1).text() for k in range(self.rowCount())]
            if targetRow == -1:  # at end
                targetRow = self.rowCount()
            # check each row to drop
            for k in range(sourceRowCount):
                rdat = [sourceInd[5 * k + j].data() for j in range(5)]
                if rdat[1] in existingKeys:
                    pass
                    # print("Duplicated row {} = {}".format(k, rdat))
                else:
                    # print("New row {} = {}".format(k, rdat))
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
    def __init__(self, rubrics):
        super(RubricWrangler, self).__init__()
        self.resize(1200, 768)
        self.model = RubricModel(rubrics)
        self.proxy = RubricProxyModel()
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
        self.rubricTable.hideColumn(1)
        ##
        self.ST = ShowListFrame(["List A", "List B", "List C"])
        ##
        self.tFiltLE = QLineEdit()
        self.tFiltLE.returnPressed.connect(self.setTextFilter)
        self.uFiltLE = QLineEdit()
        self.uFiltLE.returnPressed.connect(self.setUserFilter)
        ##
        self.curFilters = [True, False, False, True]
        self.cbQ = QCheckBox("Hide comments from other questions **recommended**")
        self.cbU = QCheckBox("Hide comments from other users (except manager)")
        self.cbM = QCheckBox("Hide comments from manager")
        self.cbS = QCheckBox("Hide system-comments **recommended**")
        #
        self.cbQ.setCheckState(Qt.Checked if self.curFilters[0] else Qt.Unchecked)
        self.cbU.setCheckState(Qt.Checked if self.curFilters[1] else Qt.Unchecked)
        self.cbM.setCheckState(Qt.Checked if self.curFilters[2] else Qt.Unchecked)
        self.cbS.setCheckState(Qt.Checked if self.curFilters[3] else Qt.Unchecked)
        ##
        self.aB = QPushButton("&Accept")
        self.aB.clicked.connect(self.returnWrangled)
        self.cB = QPushButton("&Cancel")
        self.cB.clicked.connect(self.reject)
        grid = QGridLayout()
        grid.addWidget(self.rubricTable, 1, 1, 5, 8)
        grid.addWidget(self.cbQ, 1, 9, 1, 2)
        grid.addWidget(self.cbU, 1, 11, 1, 2)
        grid.addWidget(self.cbM, 2, 9, 1, 2)
        grid.addWidget(self.cbS, 2, 11, 1, 2)
        grid.addWidget(QLabel("Filter on rubric text"), 3, 9, 1, 1)
        grid.addWidget(self.tFiltLE, 3, 10, 1, 2)
        grid.addWidget(QLabel("Filter on rubric username"), 4, 9, 1, 1)
        grid.addWidget(self.uFiltLE, 4, 10, 1, 2)
        grid.addWidget(self.ST, 5, 10, 4, 4)
        grid.addWidget(self.aB, 20, 20)
        grid.addWidget(self.cB, 20, 19)
        self.setLayout(grid)

    def setTextFilter(self):
        self.proxy.setTextFilter(self.tFiltLE.text())
        self.uFiltLE.clear()

    def setUserFilter(self):
        self.proxy.setUserFilter(self.uFiltLE.text())
        self.tFiltLE.clear()

    def toStore(self):
        store = {
            "shown": [],
            "hidden": [],
            "tabs": [],
        }
        for r in range(self.model.rowCount()):
            if self.model.index(r, 0).data(Qt.CheckStateRole) == 0:
                store["hidden"].append(self.model.index(r, 1).data())
            else:
                store["shown"].append(self.model.index(r, 1).data())
        for p in range(self.ST.STW.count()):
            store["tabs"].append([])
            for r in range(self.ST.STW.widget(p).rowCount()):
                store["tabs"][p].append(self.ST.STW.widget(p).item(r, 1).text())
        return store

    def fromStore(self, rubrics, store):
        # does not do any sanity checks
        self.model.populate(rubrics)
        self.model.setHideList(store["hidden"])
        for p in range(3):
            self.ST.populate(p, rubrics, store["tabs"][p])

    def returnWrangled(self):
        store = self.toStore()
        print("# Hidden = ", store["hidden"])
        print("# Shown = ", store["shown"])
        for p in range(self.ST.STW.count()):
            print("# Tab {} = {}".format(p, store["tabs"][p]))
        self.accept()
