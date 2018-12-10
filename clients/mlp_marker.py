import os
from shutil import copyfile
import tempfile

from examviewwindow import ExamViewWindow
from mlp_annotator import Annotator
from mlp_useful import ErrorMessage, SimpleMessage
from reorientationwindow import ExamReorientWindow

from PyQt5.QtCore import Qt, QAbstractTableModel, QElapsedTimer, QModelIndex, QPoint, QRectF, QVariant
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QDialog, QMessageBox, QWidget


import messenger
from uiFiles.ui_marker import Ui_MarkerWindow

## in order to get shortcuts under OSX this needs to set this.... but only osx.
## To test platform
import platform
if(platform.system()=='Darwin'):
    from PyQt5.QtGui import qt_set_sequence_auto_mnemonic
    qt_set_sequence_auto_mnemonic(True)

gradedColour = '#00bb00'
revertedColour = '#000099'

tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name


##########################

class TestPageGroup:
    def __init__(self, tgv, fname):
        #tgv = t0000p00v0
        #... = 0123456789
        self.prefix = tgv
        self.test = tgv[1:5]
        self.group = tgv[6:8]
        self.version = tgv[9]
        self.status = "untouched"
        self.mark = "-1"
        self.originalFile = fname
        self.annotatedFile = ""
        self.markingTime = 0

    def printMe(self):
        print( [self.prefix, self.status, self.mark, self.originalFile, self.annotatedFile, self.markingTime])

    def setstatus(self, st):
        #tgv = t0000p00v0
        #... = 0123456789
        self.status = st

    def setAnnotatedFile(self, fname):
        self.annotatedFile = fname
        self.status = "flipped"

    def setReverted(self):
        self.status = "reverted"
        self.mark = "-1"
        self.annotatedFile = ""
        self.markingTime = "0"

    def setmark(self, mrk, afname, mtime):
        #tgv = t0000p00v0
        #... = 0123456789
        self.status = "marked"
        self.mark = mrk
        self.annotatedFile = afname
        self.markingTime = mtime

class ExamModel(QAbstractTableModel):
    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.paperList = []
        self.header = ['TGV', 'Status', 'Mark', 'Time']
        self.uniqueValues = []

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
            self.paperList[index.row()].mark = value
            self.dataChanged.emit(index, index)
            return True
        elif index.column() == 3:
            self.paperList[index.row()].markingTime = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def getPaper(self, r):
        return self.paperList[r]

    def getOriginalFile(self, r):
        return self.paperList[r].originalFile

    def getAnnotatedFile(self, r):
        return self.paperList[r].annotatedFile

    def setAnnotatedFile(self, r, aname):
        self.paperList[r].annotatedFile = aname

    def setFlipped(self, index, aname):
        self.setData(index[1], 'flipped')
        self.paperList[index[0].row()].annotatedFile = aname

    def markPaper(self, index, mrk, aname, mtime):
        mt = self.data(index[3])
        self.setData(index[3], mtime+mt) #total elapsed time.
        self.setData(index[1], 'marked')
        self.setData(index[2], mrk)
        self.setAnnotatedFile(index[0].row(), aname)

    def revertPaper(self, index):
        self.setData(index[1], 'reverted')
        self.setData(index[2], -1)
        self.setData(index[3], 0)
        #remove annotated picture
        # changed to remove for windows compatibility.
        os.remove("{:s}".format(self.getAnnotatedFile(index[0].row())))

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
            return self.paperList[index.row()].mark
        elif index.column() == 3:
            return self.paperList[index.row()].markingTime
        return QVariant()

    def headerData(self, c, orientation, role):
        if role != Qt.DisplayRole:
            return
        elif orientation == Qt.Horizontal:
            return self.header[c]
        return c

##########################


class MarkerClient(QDialog):
    def __init__(self, userName, password, server, message_port, web_port, pageGroup, version):
        super(MarkerClient, self).__init__()
        messenger.setServerDetails(server, message_port, web_port)
        messenger.startMessenger()

        if not messenger.pingTest():
            self.deleteLater()
            return

        self.ui = Ui_MarkerWindow()

        self.userName = userName
        self.password = password
        self.workingDirectory = directoryPath
        self.pageGroup = pageGroup
        self.version = version
        self.maxScore = -1
        self.exM = ExamModel()

        self.ui.setupUi(self)

        self.ui.userLabel.setText(self.userName)
        self.ui.pgLabel.setText(str(self.pageGroup).zfill(2))
        self.ui.vLabel.setText(str(self.version))

        self.ui.tableView.setModel(self.exM)
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        self.ui.tableView.doubleClicked.connect(self.annotateTest)
        self.ui.tableView.annotateSignal.connect(self.annotateTest)

        self.testImg = ExamViewWindow()
        self.ui.gridLayout_6.addWidget(self.testImg, 0, 0)

        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.revertButton.clicked.connect(self.revertTest)
        # self.ui.prevButton.clicked.connect(self.moveToPrevTest)
        # self.ui.nextButton.clicked.connect(self.moveToNextTest)
        self.ui.flipButton.clicked.connect(self.flipIt)

        self.ui.markStyleGroup.setId(self.ui.markTotalRB, 1)
        self.ui.markStyleGroup.setId(self.ui.markUpRB, 2)
        self.ui.markStyleGroup.setId(self.ui.markDownRB, 3)

        self.ui.mouseHandGroup.setId(self.ui.rightMouseRB, 0)
        self.ui.mouseHandGroup.setId(self.ui.leftMouseRB, 1)

        self.requestToken()
        self.getRubric()
        self.ui.scoreLabel.setText(str(self.maxScore))
        self.requestNext()

    def requestToken(self):
        msg = messenger.SRMsg(['AUTH', self.userName, self.password])
        if msg[0] == 'ERR':
            ErrorMessage("Password problem")
            quit()
        else:
            self.token = msg[1]
            print('Token set to {}'.format(self.token))

    def shutDown(self):
        self.DNF()
        msg = messenger.SRMsg(['UCL', self.userName, self.token])
        self.close()

    def DNF(self):
        for r in range(self.exM.rowCount()):
            if self.exM.data(self.exM.index(r, 1)) != "marked":
                msg = messenger.SRMsg(['mDNF', self.userName, self.token, self.exM.data(self.exM.index(r,0))])

    def getRubric(self):
        msg = messenger.SRMsg(['mGMX', self.userName, self.token, self.pageGroup, self.version])
        if msg[0] == 'ERR':
            quit()
        self.maxScore = msg[1]

    def addTGVToList(self, paper):
        r = self.exM.addPaper(paper)
        self.ui.tableView.selectRow(r)
        self.updateImage(r)

    def updateImage(self, r=0):
        if self.exM.data(self.exM.index(r,1)) in ['marked', 'flipped']:
            self.testImg.updateImage(self.exM.getAnnotatedFile(r))
        else:
            self.testImg.updateImage(self.exM.getOriginalFile(r))
        self.ui.tableView.setFocus()


    def requestNext(self, launchAgain=False):
        msg = messenger.SRMsg(['mNUM', self.userName, self.token, self.pageGroup, self.version])
        if msg[0] == 'ERR':
            return
        fname = os.path.join(self.workingDirectory, msg[1]+".png")
        tname = msg[2]
        messenger.getFileDav(tname, fname)
        self.addTGVToList(TestPageGroup(msg[1], fname))
        # Ack that test received.
        msg = messenger.SRMsg(['mGTP', self.userName, self.token, tname])
        self.ui.tableView.resizeColumnsToContents()
        # ask server for counts update
        progress_msg = messenger.SRMsg(['mPRC', self.userName, self.token, self.pageGroup, self.version]) #returns [ACK, #id'd, #total]
        if progress_msg[0] == 'ACK':
            self.ui.mProgressBar.setValue(progress_msg[1])
            self.ui.mProgressBar.setMaximum(progress_msg[2])
        # launch annotator on the new test
        if msg[0] != 'ERR' and launchAgain:
            self.annotateTest()


    def moveToNextTest(self):
        if self.exM.rowCount() == 0:
            return
        r = self.ui.tableView.selectedIndexes()[0].row()+1
        if r > self.exM.rowCount():
            r = 0
        self.ui.tableView.selectRow(r)

    def moveToPrevTest(self):
        if self.exM.rowCount() == 0:
            return
        r = self.ui.tableView.selectedIndexes()[0].row()-1
        if r < 0:
            r = self.exM.rowCount()
        self.ui.tableView.selectRow(r)

    def moveToNextUnmarkedTest(self):
        rt = self.exM.rowCount()
        if rt == 0:
            return
        rstart = self.ui.tableView.selectedIndexes()[0].row()
        r = (rstart+1) % rt
        while self.exM.data(self.exM.index(r, 1)) == "marked" and r != rstart:
            r = (r+1) % rt
            self.ui.tableView.selectRow(r)
        if r == rstart:
            return False
        return True

    def revertTest(self):
        index = self.ui.tableView.selectedIndexes()
        if len(index)==0:
            return #fixes a crash found by Patrick

        if(self.exM.data(index[1]) in ["untouched", "reverted"]):
            return
        msg = SimpleMessage('Do you want to revert to original scan?')
        if msg.exec_() == QMessageBox.No:
            return
        self.exM.revertPaper(index)
        self.updateImage(index[0].row())

    def waitForAnnotator(self, fname):
        timer = QElapsedTimer()
        timer.start()
        self.markStyle = self.ui.markStyleGroup.checkedId()
        self.mouseHand = self.ui.mouseHandGroup.checkedId()

        annotator = Annotator(fname, self.maxScore, self.markStyle, self.mouseHand)
        if annotator.exec_():
            if annotator.score >= 0:
                return [str(annotator.score), timer.elapsed()//1000, annotator.launchAgain] #number of seconds rounded down.
            else:
                msg = ErrorMessage('You have to give a mark.')
                msg.exec_()
                return self.waitForAnnotator(fname)
        else:
            msg = ErrorMessage("mark not recorded")
            msg.exec_()
            return [None, timer.elapsed(), False]

    def writeGradeOnImage(self,fname,gr):
        img = QPixmap(fname)
        font = QFont("Helvetica")
        font.setPointSize(30)
        text = " {} out of {} ".format(str(gr).zfill(2), self.maxScore)
        painter = QPainter()
        painter.begin(img)
        painter.setFont(font)
        brect = painter.fontMetrics().boundingRect(text)
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawRoundedRect(QRectF(5, 5, brect.width()+30, brect.height()+30), 5, 5)
        painter.drawText(QPoint(20-brect.left(), 24-brect.top()), text)
        painter.end()
        img.save(fname)

    def annotateTest(self):
        if self.exM.rowCount() == 0:
            return
        index = self.ui.tableView.selectedIndexes()

        if self.exM.data(index[1]) == 'marked':
            msg = SimpleMessage('Do you want to annotate further?')
            if msg.exec_() == QMessageBox.No:
                return

        aname = os.path.join(self.workingDirectory, "G" + self.exM.data(index[0])[1:] + ".png")
        if self.exM.data(index[1]) in ['untouched', 'reverted']:
            copyfile("{:s}".format(self.exM.getOriginalFile(index[0].row())), aname)

        [gr, mtime, launchAgain] = self.waitForAnnotator(aname)
        if gr is None: #Exited annotator with 'cancel'
            return

        self.exM.markPaper(index, gr, aname, mtime)
        # self.writeGradeOnImage(aname, gr)

        dname = os.path.basename(aname)
        messenger.putFileDav(aname, dname)

        msg = messenger.SRMsg(['mRMD', self.userName, self.token, self.exM.data(index[0]), gr, dname, mtime])

        if self.moveToNextUnmarkedTest() == False:
            self.requestNext(launchAgain)


    def waitForFlipper(self, fname):
        flipper = ExamReorientWindow(fname)
        if flipper.exec_() == QDialog.Accepted:
            return True
        else:
            return False

    def flipIt(self):
        index = self.ui.tableView.selectedIndexes()
        aname = os.path.join(self.workingDirectory, "G" + self.exM.data(index[0])[1:] + ".png")
        if(self.exM.data(index[1]) in ['untouched', 'reverted']):
            copyfile("{:s}".format(self.exM.getOriginalFile(index[0].row())), aname)

            if self.waitForFlipper(aname) == True:
                self.exM.setFlipped(index, aname)
                self.updateImage(index[0].row())
        else:
            msg = ErrorMessage('Can only flip original or reverted test.')
            msg.exec_()

    def selChanged(self, selnew, selold):
        self.updateImage(selnew.indexes()[0].row())
