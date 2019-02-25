__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

from collections import defaultdict
from datetime import datetime
import json
import sys
import tempfile
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QDialog,
    QGridLayout,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel
from examviewwindow import ExamViewWindow


class errorMessage(QMessageBox):
    def __init__(self, txt):
        super(errorMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class simpleMessage(QMessageBox):
    def __init__(self, txt):
        super(simpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)


class SimpleTableView(QTableView):
    def __init__(self, model):
        QTableView.__init__(self)
        self.setModel(model)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.parent().requestPageImage(self.selectedIndexes()[0])
        else:
            super(SimpleTableView, self).keyPressEvent(event)


class FilterComboBox(QComboBox):
    def __init__(self, txt):
        QWidget.__init__(self)
        self.title = txt
        self.addItem(txt)


class ExamTable(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("../resources/identity.db")
        self.db.setHostName("Andrew")
        self.db.open()
        self.initUI()
        self.loadData()
        self.setFilterOptions()

    def initUI(self):
        grid = QGridLayout()
        self.exM = QSqlTableModel(self, self.db)
        self.exM.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.exM.setTable("idimage")
        self.exV = SimpleTableView(self.exM)

        grid.addWidget(self.exV, 0, 0, 4, 7)

        self.filterGo = QPushButton("Filter Now")
        self.filterGo.clicked.connect(self.filter)
        grid.addWidget(self.filterGo, 5, 0)
        self.flU = FilterComboBox("Marker")
        grid.addWidget(self.flU, 5, 2)
        self.flS = FilterComboBox("Status")
        grid.addWidget(self.flS, 5, 3)

        self.revertB = QPushButton("Revert")
        self.revertB.clicked.connect(lambda: self.revertCurrent())
        grid.addWidget(self.revertB, 2, 8)

        self.pgImg = ExamViewWindow()
        grid.addWidget(self.pgImg, 0, 10, 20, 20)

        self.setLayout(grid)
        self.show()

    def requestPageImage(self, index):
        rec = self.exM.record(index.row())
        self.pgImg.updateImage(
            "../scanAndGroup/readyForMarking/idgroup/{}.png".format(rec.value("tgv"))
        )

    def computeUserProgress(self):
        ustats = defaultdict(lambda: [0, 0])
        for r in range(self.exM.rowCount()):
            if self.exM.record(r).value("user") == "None":
                continue
            ustats[self.exM.record(r).value("user")][0] += 1
            if self.exM.record(r).value("status") == "Identified":
                ustats[self.exM.record(r).value("user")][1] += 1
        UserProgress(ustats).exec_()

    def getUniqueFromColumn(self, col):
        lst = set()
        query = QSqlQuery(db=self.db)
        print(query.exec_("select {} from idimage".format(col)))
        while query.next():
            lst.add(str(query.value(0)))
        return sorted(list(lst))

    def loadData(self):
        for c in [0, 1]:
            self.exV.hideColumn(c)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def setFilterOptions(self):
        self.flS.insertItems(1, self.getUniqueFromColumn("status"))
        self.flU.insertItems(1, self.getUniqueFromColumn("user"))

    def filter(self):
        flt = []
        if self.flS.currentText() != "Status":
            flt.append("status='{}'".format(self.flS.currentText()))
        if self.flU.currentText() != "Marker":
            flt.append("user='{}'".format(self.flU.currentText()))

        if len(flt) > 0:
            flts = " AND ".join(flt)
        else:
            flts = ""
        self.exM.setFilter(flts)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def revertCurrent(self):
        indices = self.exV.selectedIndexes()
        if len(indices) is 0:
            return
        currentRow = indices[0].row()
        rec = self.exM.record(currentRow)
        if rec.value("status") == "ToDo":
            msg = errorMessage(
                'TGV {} is still "ToDo" - no action taken'.format(rec.value("tgv"))
            )
            msg.exec_()
            return
        msg = simpleMessage(
            'TGV {} has status "{}" - do you wish to revert'.format(
                rec.value("tgv"), rec.value("status")
            )
        )
        if msg.exec_() == QMessageBox.No:
            return
        # Revert status
        rec.setValue("status", "ToDo")
        rec.setValue("user", "None")
        rec.setValue("time", "{}".format(datetime.now()))
        rec.setValue("sname", "")
        # grab test number so we can set SID to -TestNumber so it is still unique
        t = rec.value("number")
        rec.setValue("sid", -t)
        # update the row
        self.exM.setRecord(currentRow, rec)
        # and update the database
        self.exM.submitAll()


class Manager(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        self.extb = ExamTable()
        grid.addWidget(self.extb, 1, 1, 4, 6)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(self.close)
        grid.addWidget(self.closeB, 6, 99)

        self.setLayout(grid)
        self.setWindowTitle("Where we are at.")
        self.show()


tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

app = QApplication(sys.argv)
iic = Manager()
app.exec_()
