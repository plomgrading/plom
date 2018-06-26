from examviewwindow import ExamViewWindow
from mlp_useful import ErrorMessage, SimpleMessage
import tempfile


from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QStringListModel, QVariant
from PyQt5.QtWidgets import QCompleter, QDialog, QMessageBox, QWidget

import csv
from collections import defaultdict
import time

###
from uiFiles.ui_identify import Ui_IdentifyWindow
import mlp_messenger

tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

identifiedColor = '#00bb00'

class Paper:
    def __init__(self, tgv, fname):
        #tgv = t0000p00v0
        #... = 0123456789
        self.prefix = tgv
        self.test = tgv[1:5]
        self.status = "unidentified"
        self.sname = ""
        self.sid = ""
        self.originalFile = fname

    def printMe(self):
        print([self.prefix, self.status, self.sid, self.sname, self.originalFile])

    def setStatus(self, st):
        self.status = st

    def setReverted(self):
        self.status = "unidentified"
        self.sid = "-1"
        self.sname = "unknown"

    def setID(self, sid, sname):
        #tgv = t0000p00v0
        #... = 0123456789
        self.status = "identified"
        self.sid = sid
        self.sname=sname


class ExamModel(QAbstractTableModel):
    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.paperList = []
        self.header = ['Code', 'Status', 'ID', 'Name']

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        if index.column() == 0:
            self.paperList[index.row()].prefix = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 1:
            self.paperList[index.row()].status = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 2:
            self.paperList[index.row()].sid = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 3:
            self.paperList[index.row()].sname = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def identifyStudent(self, index, sid, sname):
        self.setData(index[1], 'identified')
        self.setData(index[2], sid)
        self.setData(index[3], sname)

    def revertStudent(self, index):
        self.setData(index[1], 'unidentified')
        self.setData(index[2], '')
        self.setData(index[3], '')

    def addPaper(self, rho):
        r = self.rowCount()
        self.beginInsertRows(QModelIndex(), r, r)
        self.paperList.append(rho)
        self.endInsertRows()
        return r

    def rowCount(self, parent=None):
        return len(self.paperList)
    def columnCount(self, parent=None):
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        elif index.column() == 0:
            return self.paperList[index.row()].prefix
        elif index.column() == 1:
            return self.paperList[index.row()].status
        elif index.column() == 2:
            return self.paperList[index.row()].sid
        elif index.column() == 3:
            return self.paperList[index.row()].sname
        return QVariant()

    def headerData(self, c, orientation, role):
        if role != Qt.DisplayRole:
            return
        elif orientation == Qt.Horizontal:
            return self.header[c]
        return c

class IDClient(QWidget):
    def __init__(self, userName, password, server, message_port, web_port):
        super(IDClient, self).__init__()

        mlp_messenger.setServerDetails(server, message_port, web_port)
        mlp_messenger.startMessenger()

        if not mlp_messenger.pingTest():
            self.deleteLater()
            return

        self.ui = Ui_IdentifyWindow()

        self.userName = userName
        self.password = password
        self.workingDirectory = directoryPath
        self.requestToken()
        self.getClassList()
        self.paperList = []
        self.unidCount = 0
        self.exM = ExamModel()
        self.ui.setupUi(self)

        self.ui.userLabel.setText(self.userName)
        self.ui.tableView.setModel(self.exM)
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)

        self.testImg = ExamViewWindow()
        self.ui.gridLayout_7.addWidget(self.testImg, 0, 0)

        self.setCompleters()
        self.ui.idEdit.returnPressed.connect(self.duh)
        self.ui.nameEdit.returnPressed.connect(self.enterName)
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.nextButton.clicked.connect(self.requestNext)

    def duh(self):
        self.enterID()
        self.ui.paperBox.setFocus()

    def requestToken(self):
        msg = mlp_messenger.SRMsg(['AUTH', self.userName, self.password])
        if msg[0] == 'ERR':
            ErrorMessage("Password problem")
            quit()
        else:
            self.token = msg[1]
            print('Token set to {}'.format(self.token))

    def getClassList(self):
        msg = mlp_messenger.SRMsg(['iRCL', self.userName, self.token])
        if msg[0] == 'ERR':
            ErrorMessage("Classlist problem")
            quit()
        dfn = msg[1]
        fname = self.workingDirectory + "/cl.csv"
        mlp_messenger.getFileDav(dfn, fname)
        # read classlist into dictionaries
        self.studentNamesToNumbers = defaultdict(int)
        self.studentNumbersToNames = defaultdict(str)
        with open(fname) as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            for row in reader:
                sn = row['surname']+', '+row['name']
                self.studentNamesToNumbers[sn] = str(row['id'])
                self.studentNumbersToNames[str(row['id'])] = sn
          #acknowledge class list
        msg = mlp_messenger.SRMsg(['iGCL', self.userName, self.token, dfn])
        if msg[0] == 'ERR':
            ErrorMessage("Classlist problem")
            quit()
        return True

    def setCompleters(self):
        self.sidlist = QStringListModel()
        self.snamelist = QStringListModel()

        self.sidlist.setStringList(list(self.studentNumbersToNames.keys()))
        self.snamelist.setStringList(list(self.studentNamesToNumbers.keys()))

        self.sidcompleter = QCompleter()
        self.sidcompleter.setModel(self.sidlist)
        self.snamecompleter = QCompleter()
        self.snamecompleter.setModel(self.snamelist)

        self.ui.idEdit.setCompleter(self.sidcompleter)
        self.ui.nameEdit.setCompleter(self.snamecompleter)

    def shutDown(self):
        self.DNF()
        msg = mlp_messenger.SRMsg(['UCL', self.userName, self.token])
        self.close()

    def DNF(self):
        rc = self.exM.rowCount()
        for r in range(rc):
            if self.exM.data(self.exM.index(r, 1)) != "identified":
                msg = mlp_messenger.SRMsg(['iDNF', self.userName, self.token, self.exM.data(self.exM.index(r, 0))])

    def selChanged(self, selnew, selold):
        self.ui.idEdit.setText(self.exM.data(selnew.indexes()[2]))
        self.ui.nameEdit.setText(self.exM.data(selnew.indexes()[3]))
        self.updateImage(selnew.indexes()[0].row())

    def updateImage(self, r=0):
        self.testImg.updateImage(self.exM.paperList[r].originalFile)

    def addPaperToList(self, paper):
        r = self.exM.addPaper(paper)
        self.ui.tableView.selectRow(r)
        self.updateImage(r)
        self.unidCount += 1

    def requestNext(self):
        # ask server for next unid'd paper >>> test,fname = server.nextUnIDd(self.userName)
        msg = mlp_messenger.SRMsg(['iNID', self.userName, self.token])
        if msg[0] == 'ERR':
            return
        test = msg[1]
        fname = msg[2]
        iname = self.workingDirectory+"/"+test+".png"
        mlp_messenger.getFileDav(fname, iname)
        self.addPaperToList(Paper(test, iname))
        #acknowledge got test  >>>   server.gotTest(self.userName, test, fname)
        msg = mlp_messenger.SRMsg(['iGTP', self.userName, self.token, test, fname])
        self.ui.tableView.resizeColumnsToContents()

    def identifyStudent(self, index, alreadyIDd=False):
        self.exM.identifyStudent(index, self.ui.idEdit.text(),self.ui.nameEdit.text())
        code = self.exM.data(index[0])
        if alreadyIDd:
            msg = mlp_messenger.SRMsg(['iRAD', self.userName, self.token, code, self.ui.idEdit.text(), self.nameEdit.text()])
        else:
            msg = mlp_messenger.SRMsg(['iRID', self.userName, self.token, code, self.ui.idEdit.text(), self.ui.nameEdit.text()])
        if msg[0] == 'ERR':
            self.exM.revertStudent(index)
            self.ui.idEdit.setText("")
            self.ui.nameEdit.setText("")
            return False
        else:
            self.unidCount -= 1
            return True

    def moveToNextUnID(self):
        rt = self.exM.rowCount()
        if rt == 0:
            return
        rstart = self.ui.tableView.selectedIndexes()[0].row()
        r = (rstart+1) %  rt
        while(self.exM.data(self.exM.index(r, 2)) == "identified" and  r != rstart):
            r = (r+1) %  rt
        self.ui.tableView.selectRow(r)

    def enterID(self):
        if self.exM.rowCount() == 0:
            return
        index = self.ui.tableView.selectedIndexes()
        code = self.exM.data(index[0])
        if code == None:
            return
        status = self.exM.data(index[1])
        alreadyIDd = False

        if status == "identified":
            msg = SimpleMessage('Do you want to change the ID?')
            if msg.exec_() == QMessageBox.No:
                return
            else:
                alreadyIDd = True

        if self.ui.idEdit.text() in self.studentNumbersToNames:
            self.ui.nameEdit.setText(self.studentNumbersToNames[self.ui.idEdit.text()])
            msg = SimpleMessage('Student ID {:s} = {:s}. Enter and move to next?'.format(self.ui.idEdit.text(),self.ui.nameEdit.text()))
            if msg.exec_() == QMessageBox.No:
                return
        else:
            msg = SimpleMessage('Student ID {:s} not in list. Do you want to enter it anyway?'.format(self.ui.idEdit.text()))
            if msg.exec_() == QMessageBox.No:
                return
            self.ui.nameEdit.setText("Unknown")

        if self.identifyStudent(index, alreadyIDd):
            if alreadyIDd == False and self.unidCount == 0:
                self.requestNext()
            else:
                self.moveToNextUnID()
        return

    def enterName(self):
        if self.exM.rowCount() == 0:
            return
        index = self.ui.tableView.selectedIndexes()
        code = self.exM.data(index[0])
        if code == None:
            return
        status = self.exM.data(index[1])
        alreadyIDd = False

        if status == "identified":
            msg = SimpleMessage('Do you want to change the ID?')
            if msg.exec_() == QMessageBox.No:
                return
            else:
                alreadyIDd = True

        if self.ui.nameEdit.text() in self.studentNamesToNumbers:
            self.ui.idEdit.setText(self.studentNamesToNumbers[self.ui.nameEdit.text()])
            msg = SimpleMessage( 'Student ID {:s} = {:s}. Enter and move to next?'.format(self.ui.idEdit.text(),self.ui.nameEdit.text()))
            if msg.exec_() == QMessageBox.No:
                return
        else:
            msg = SimpleMessage('Student ID {:s} not in list. Do you want to enter it anyway?'.format(self.ui.idEdit.text()))
            if msg.exec_() == QMessageBox.No:
                return
            self.ui.nameEdit.setText("Unknown")

        if self.identifyStudent(index, alreadyIDd):
            if alreadyIDd == False and self.unidCount == 0:
                self.requestNext()
            else:
                self.moveToNextUnID()
        return
