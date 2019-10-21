__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import sys
import tempfile
import json
import asyncio
from datetime import datetime
import ssl
from collections import defaultdict
from examviewwindow import ExamViewWindow
import os
import shutil
import glob
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from PyQt5.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel


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


class simpleTableView(QTableView):
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
            super(QTableView, self).keyPressEvent(event)


class filterComboBox(QComboBox):
    def __init__(self, txt):
        QWidget.__init__(self)
        self.title = txt
        self.addItem(txt)


class examTable(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("../resources/test_marks.db")
        self.db.setHostName("Andrew")
        self.db.open()
        self.initUI()
        self.loadData()
        self.setFilterOptions()

    def initUI(self):
        grid = QGridLayout()
        self.exM = QSqlTableModel(self, self.db)
        self.exM.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.exM.setTable("groupimage")
        self.exV = simpleTableView(self.exM)

        grid.addWidget(self.exV, 0, 0, 4, 7)

        self.filterGo = QPushButton("Filter Now")
        self.filterGo.clicked.connect(lambda: self.filter())
        grid.addWidget(self.filterGo, 5, 0)
        self.flP = filterComboBox("PageGroup")
        grid.addWidget(self.flP, 5, 2)
        self.flV = filterComboBox("Version")
        grid.addWidget(self.flV, 5, 3)
        self.flS = filterComboBox("Status")
        grid.addWidget(self.flS, 5, 4)
        self.flU = filterComboBox("Marker")
        grid.addWidget(self.flU, 5, 5)
        self.flM = filterComboBox("Mark")
        grid.addWidget(self.flM, 5, 6)
        self.flT = QLineEdit()
        self.flT.setMaxLength(256)
        self.flT.setPlaceholderText("Filter on tag text")
        self.flT.setClearButtonEnabled(True)
        grid.addWidget(self.flT, 6, 5, 1, 2)

        self.revertB = QPushButton("Revert")
        self.revertB.clicked.connect(lambda: self.revertCurrent())
        grid.addWidget(self.revertB, 1, 8)

        self.pgImg = ExamViewWindow()
        grid.addWidget(self.pgImg, 0, 10, 20, 20)

        self.setLayout(grid)
        self.show()

    def requestPageImage(self, index):
        rec = self.exM.record(index.row())
        if rec.value("status") == "Marked":
            self.pgImg.updateImage(
                "./markedPapers/{}".format(rec.value("annotatedFile"))
            )
        else:
            self.pgImg.updateImage(rec.value("originalFile"))

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
        # Revert status and delete any annotated file.
        rec.setValue("status", "ToDo")
        rec.setValue("user", "None")
        rec.setValue("time", "{}".format(datetime.now()))
        rec.setValue("mark", -1)
        rec.setValue("markingTime", 0)
        # Move annotated file to a sensible subdirectory...
        # Check if subdir exists
        if not os.path.exists("markedPapers/revertedPapers"):
            os.makedirs("markedPapers/revertedPapers")
        # Move the png file
        fname = rec.value("annotatedFile")
        try:
            shutil.move("markedPapers/" + fname, "markedPapers/revertedPapers/")
        except FileNotFoundError:
            print('failed to move png file')
        # and any old .png.regraded files
        for f in glob.glob("markedPapers/" + fname + '.regrade*'):
            try:
                shutil.move(f, "markedPapers/revertedPapers/")
            except FileNotFoundError:
                print('failed to move .png.regrade file: ' + f)
        # And move the associated textfile.
        fname += ".txt"
        try:
            shutil.move("markedPapers/" + fname, "markedPapers/revertedPapers/")
        except FileNotFoundError:
            print('failed to move txt file')

        # now safe to set the annotatedFile value in the record
        rec.setValue("annotatedFile", "")
        # move the plomFile and commentFile too
        fname = rec.value("plomFile")
        try:
            shutil.move("markedPapers/plomFiles/" + fname, "markedPapers/revertedPapers/")
        except FileNotFoundError:
            print('failed to move plom file')
        rec.setValue("plomFile", "")
        fname = rec.value("commentFile")
        try:
            shutil.move("markedPapers/commentFiles/" + fname, "markedPapers/revertedPapers/")
        except FileNotFoundError:
            print('failed to move comment file')
        rec.setValue("commentFile", "")
        # clear the tags
        rec.setValue("tags", "")
        # update the row
        self.exM.setRecord(currentRow, rec)
        # and update the database
        self.exM.submitAll()

    def getUniqueFromColumn(self, col):
        lst = set()
        query = QSqlQuery(db=self.db)
        query.exec_("select {} from groupimage".format(col))
        while query.next():
            lst.add(str(query.value(0)))
        return sorted(list(lst))

    def loadData(self):
        # A row of the table in the Mark DB is
        # 0=index, 1=TGV, 2=originalFile, 3=testnumber, 4=pageGroup
        # 5=version, 6=annotatedFile, 7=plomFile, 8=commentFile,
        # 9=status, 10=user, 11=time, 12=mark, 13=timeSpentMarking,
        # 14=tags
        for c in [0, 2, 3, 6, 7, 8]:
            self.exV.hideColumn(c)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def setFilterOptions(self):
        self.flP.insertItems(1, self.getUniqueFromColumn("pageGroup"))
        self.flV.insertItems(1, self.getUniqueFromColumn("version"))
        self.flS.insertItems(1, self.getUniqueFromColumn("status"))
        self.flU.insertItems(1, self.getUniqueFromColumn("user"))
        self.flM.insertItems(1, self.getUniqueFromColumn("mark"))

    def filter(self):
        flt = []
        if self.flP.currentText() != "PageGroup":
            flt.append("pageGroup='{}'".format(self.flP.currentText()))
        if self.flV.currentText() != "Version":
            flt.append("version='{}'".format(self.flV.currentText()))
        if self.flS.currentText() != "Status":
            flt.append("status='{}'".format(self.flS.currentText()))
        if self.flU.currentText() != "Marker":
            flt.append("user='{}'".format(self.flU.currentText()))
        if self.flM.currentText() != "Mark":
            flt.append("mark='{}'".format(self.flM.currentText()))
        # and filter on tag
        txt = self.flT.text().strip()
        if len(txt) > 0:
            flt.append("tags LIKE '%{}%'".format(txt))

        if len(flt) > 0:
            flts = " AND ".join(flt)
        else:
            flts = ""
            # reset filter options
            self.setFilterOptions()

        self.exM.setFilter(flts)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)


class manager(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        self.extb = examTable()

        grid.addWidget(self.extb, 1, 1, 4, 6)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(lambda: self.close())
        grid.addWidget(self.closeB, 6, 99)

        self.setLayout(grid)
        self.setWindowTitle("Where we are at.")
        self.show()


tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

app = QApplication(sys.argv)
iic = manager()
app.exec_()
