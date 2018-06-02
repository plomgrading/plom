import sys, os, glob, argparse, datetime, tempfile, json
from os import path
import easywebdav2, asyncio, ssl

from testpagegroup import TestPageGroup
from painter import Painter
from gui_utils import ErrorMessage, SimpleMessage, StartUpMarkerWidget
from reorientationwindow import ExamReorientWindow

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QPoint, QRectF, QVariant
from PyQt5.QtGui import QBrush, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QDialog, QGridLayout, QLabel, QMessageBox, QPushButton, QSizePolicy, QTableView, QWidget

gradedColour = '#00bb00'
revertedColour = '#000099'

webdav_user = 'hack'
webdav_passwd = 'duhbah'
server = 'localhost'
webdav_port=41985
message_port=41984

# # # # # # # # # # # #
# How do we avoid having to distribute the crt to the client?
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# # # # # # # # # # # #

async def handle_messaging(msg):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    print("Sending message {}",format(msg))
    jm = json.dumps(msg)
    writer.write(jm.encode())
    # SSL does not support EOF, so send a null byte to indicate the end of the message.
    writer.write(b'\x00')
    await writer.drain()

    data = await reader.read(100)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    rmesg = json.loads( data.decode() ) # message should be a list [cmd, user, arg1, arg2, etc]
    writer.close()
    print("Got message {}".format(rmesg))
    return(rmesg)

def SRMsg(msg):
    rmsg = loop.run_until_complete(handle_messaging(msg))
    if( rmsg[0] == 'ACK'):
        return(rmsg)
    elif( rmsg[0] == 'ERR'):
        # print("Some sort of error occurred - didnt get an ACK, instead got ", rmsg)
        msg = ErrorMessage(rmsg[1])
        msg.exec_()
        return(rmsg)
    else:
        msg = ErrorMessage("Something really wrong has happened.")
        self.Close()

def getFileDav(dfn, lfn):
  webdav = easywebdav2.connect(server, port=webdav_port, username=webdav_user, password=webdav_passwd)
  try:
    argh = webdav.download(dfn,lfn)
  except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print( message)

def putFileDav(lfn,dfn):
  webdav = easywebdav2.connect(server, port=webdav_port, username=webdav_user, password=webdav_passwd)
  try:
    argh = webdav.upload(lfn,dfn)
  except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print( message)

###

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
             self.parent().annotateTest()
         else:
             super(QTableView, self).keyPressEvent(event)
##########################

class ExamModel(QAbstractTableModel):
    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.paperList=[]
        self.header=['TestGroupVersion','Status','Mark']
        self.uniqueValues=[]

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False
        if(index.column()==0):
            self.paperList[index.row()].prefix=value
            self.dataChanged.emit(index, index)
            return True
        elif(index.column()==1):
            self.paperList[index.row()].status=value
            self.dataChanged.emit(index, index)
            return True
        elif(index.column()==2):
            self.paperList[index.row()].mark=value
            self.dataChanged.emit(index, index)
            return True
        return False

    def getPaper(self, r):
        return(self.paperList[r])
    def getOriginalFile(self, r):
        return(self.paperList[r].originalFile)
    def getAnnotatedFile(self, r):
        return(self.paperList[r].annotatedFile)
    def setAnnotatedFile(self, r, aname):
        self.paperList[r].annotatedFile=aname
    def setFlipped(self, index, aname):
        self.setData(index[1],'flipped')
        self.paperList[index[0].row()].annotatedFile=aname

    def markPaper(self, index, mrk, aname):
        self.setData(index[1],'marked')
        self.setData(index[2],mrk)
        self.setAnnotatedFile( index[0].row(), aname )

    def revertPaper(self, index):
        self.setData(index[1],'reverted')
        self.setData(index[2],-1)
        os.system("rm -f {:s}".format( self.getAnnotatedFile(index[0].row()) ) ) #remove annotated picture

    def addPaper(self, rho):
        r=self.rowCount()
        self.beginInsertRows(QModelIndex(), r,r)
        self.paperList.append(rho)
        self.endInsertRows()
        return(r)

    def rowCount(self, parent=None):
        return(len(self.paperList))
    def columnCount(self, parent=None):
        return 3

    def data(self, index, role=Qt.DisplayRole):
        if( role != Qt.DisplayRole ):
            return QVariant()
        elif(index.column()==0):
            return self.paperList[index.row()].prefix
        elif(index.column()==1):
            return self.paperList[index.row()].status
        elif(index.column()==2):
            return self.paperList[index.row()].mark
        else:
            return QVariant()

    def headerData(self, c, orientation, role):
        if( role != Qt.DisplayRole ):
            return
        elif( orientation == Qt.Horizontal ):
            return(self.header[c])
        return c

##########################


class Grader(QWidget):
    def __init__(self, userName, password, pageGroup, version):
        super(Grader, self).__init__()

        self.exM = ExamModel()
        self.exV = SimpleTableView(self.exM)

        self.pageGroup=pageGroup
        self.version=version

        self.userName=userName
        self.password=password
        self.requestToken()

        self.tempDirectory = tempfile.TemporaryDirectory()
        self.workingDirectory = tempDirectory.name

        self.getRubric()
        self.initUI()

    def requestToken(self):
        msg = SRMsg(['AUTH', self.userName, self.password])
        if(msg[0]=='ERR'):
            ErrorMessage("Password problem")
            quit()
        else:
            self.token=msg[1]
            print('Token set to {}'.format(self.token))

    def shutDown(self):
        self.DNF()
        msg = SRMsg(['UCL', self.userName, self.token])
        self.close()

    def DNF(self):
      rc = self.exM.rowCount()
      for r in range(rc):
          if( self.exM.data(self.exM.index(r,1) ) != "marked" ):
            msg = SRMsg(['mDNF', self.userName, self.token, self.exM.data(self.exM.index(r,0) )])

    def getRubric(self):
        msg = SRMsg(['mGMX', self.userName, self.token, self.pageGroup, self.version])
        if(msg[0]=='ERR'):
            self.shutDown()
        self.maxScore=msg[1]

    def addTGVToList(self, paper):
      r =self.exM.addPaper(paper)
      self.exV.selectRow( r )
      self.updateImage(r)

    def updateImage(self, r=0):
      if( self.exM.data(self.exM.index(r,1)) in ['marked', 'flipped'] ):
          testpix = QPixmap( self.exM.getAnnotatedFile(r) )
      else:
          testpix = QPixmap( self.exM.getOriginalFile(r) )
      self.pageImg.setPixmap( testpix.scaledToWidth(1200) )
      self.exV.setFocus()

    def requestNext(self):
        msg = SRMsg(['mNUM', self.userName, self.token, self.pageGroup, self.version])
        fname = self.workingDirectory+"/"+msg[1]+".png"
        tname = msg[2]
        getFileDav(tname, fname)
        self.addTGVToList( TestPageGroup(msg[1],fname) )
        # Ack that test received.
        msg = SRMsg(['mGTP', self.userName, self.token, tname])


    def moveToNextTest(self):
        r = self.exV.selectedIndexes()[0].row()+1
        if(r > self.exM.rowCount()):
            r=0
        self.exV.selectRow(r)

    def moveToPrevTest(self):
        r = self.exV.selectedIndexes()[0].row()-1
        if(r < 0):
            r = self.exM.rowCount()
        self.exV.selectRow(r)

    def moveToNextUnmarkedTest(self):
        rt = self.exM.rowCount()
        if(rt==0):
            return
        rstart = self.exV.selectedIndexes()[0].row()
        r = (rstart+1) %  rt
        while(self.exM.data(self.exM.index(r,1) ) == "marked" and  r != rstart):
            r = (r+1) %  rt
            self.exV.selectRow(r)
        if(r==rstart):
            return(False)
        return(True)

    def revertTest(self):
        index = self.exV.selectedIndexes()
        if(self.exM.data(index[1]) in ["untouched", "reverted"]):
            return
        msg = SimpleMessage('Do you want to revert to original scan?')
        if( msg.exec_() == QMessageBox.No ):
            return
        self.exM.revertPaper(index)
        self.updateImage(index[0].row())

    def annotateTestFurther(self):
        if(self.exM.rowCount()==0):
            return
        index = self.exV.selectedIndexes()
        if(self.exM.data(index[1]) in ["untouched", "reverted"]):
            return
        msg = SimpleMessage('Do you want to annotate further?')
        if(msg.exec_()==QMessageBox.No):
            return
        self.annotateTest()

    def waitForPainter(self, fname):
        annot=Painter(fname, self.maxScore)
        if( annot.exec_() ):
            if( annot.gradeCurrentScore.text() != "-1" ):
              return( annot.gradeCurrentScore.text() )
            else:
              return( self.waitForPainter(fname) )
        else:
            return None

    def writeGradeOnImage(self,fname,gr):
        img = QPixmap(fname)
        font = QFont("Helvetica"); font.setPointSize(24)
        text = " {} out of {} ".format(str(gr).zfill(2), self.maxScore)
        painter=QPainter()
        painter.begin(img)
        painter.setFont( font )
        brect = painter.fontMetrics().boundingRect(text)
        painter.setPen(QPen(Qt.red,2))
        painter.setBrush(QBrush(Qt.white))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawRoundedRect(QRectF(4,4,brect.width()+24, brect.height()+24),4,4)
        painter.drawText( QPoint(16-brect.left(),16-brect.top()), text )
        painter.end()
        img.save(fname)

    def annotateTest(self):
        if(self.exM.rowCount()==0):
            return
        index = self.exV.selectedIndexes()
        aname = self.workingDirectory + "/G" + self.exM.data(index[0])[1:] + ".png"
        if(self.exM.data(index[1]) in ['untouched', 'reverted']):
           os.system("cp {:s} {:s}".format(self.exM.getOriginalFile(index[0].row()), aname) )

        gr = self.waitForPainter(aname)
        if(gr==None): #Exited annotator with 'cancel'
            return

        self.exM.markPaper(index,gr,aname)
        self.writeGradeOnImage(aname,gr)
        os.system("ls -l {}".format(aname))

        dname = os.path.basename(aname)
        putFileDav(aname, dname)
        msg = SRMsg(['mRMD', self.userName, self.token, self.exM.data(index[0]), gr, dname])

        if(self.moveToNextUnmarkedTest()==False):
            self.requestNext()

    def waitForFlipper(self, fname):
        flipper=ExamReorientWindow(fname)
        if(flipper.exec_()==QDialog.Accepted):
            return(True)
        else:
            return(False)

    def flipIt(self):
        index = self.exV.selectedIndexes()
        aname = self.workingDirectory + "/G" + self.exM.data(index[0])[1:] + ".png"
        if(self.exM.data(index[1]) in ['untouched', 'reverted']):
           os.system("cp {:s} {:s}".format(self.exM.getOriginalFile(index[0].row()), aname) )
           if( self.waitForFlipper(aname)==True ):
               self.exM.setFlipped(index, aname)
               self.updateImage(index[0].row())
        else:
            msg = ErrorMessage('Can only flip original or reverted test.')
            msg.exec_()

    def selChanged(self, selnew, selold):
          self.updateImage( selnew.indexes()[0].row() )

    def initUI(self):
        grid = QGridLayout()
        ###
        self.name = QLabel('Grader Name:')
        self.nameOfGrader = QLabel(self.userName)
        grid.addWidget(self.name, 1, 0)
        grid.addWidget(self.nameOfGrader, 1, 1)

        self.ms = QLabel('Max Score:')
        self.msD = QLabel(str(self.maxScore))
        grid.addWidget(self.ms, 1, 2)
        grid.addWidget(self.msD, 1, 3)

        self.test = QLabel('Current Test')
        self.testName = QLabel()
        self.pageL = QLabel('PageGroup ')
        self.pageName = QLabel(self.pageGroup)
        self.versionL = QLabel('Version ')
        self.versionName = QLabel(self.version)
        grid.addWidget(self.test, 2, 0)
        grid.addWidget(self.testName, 2, 1)
        grid.addWidget(self.pageL, 3, 0)
        grid.addWidget(self.pageName, 3, 1)
        grid.addWidget(self.versionL, 3, 2)
        grid.addWidget(self.versionName, 3, 3)

        ###
        self.flipB = QPushButton("UpsideDown")
        self.flipB.clicked.connect(lambda:self.flipIt())
        grid.addWidget(self.flipB,99,12)
        ###
        self.closeB = QPushButton("Close")
        self.closeB.clicked.connect(lambda:self.shutDown())
        grid.addWidget(self.closeB,100,1)

        ###
        self.exV.setModel(self.exM)
        self.exV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.exV.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exV.selectionModel().selectionChanged.connect(self.selChanged)
        self.exV.doubleClicked.connect(lambda: self.annotateTest())
        grid.addWidget(self.exV, 7, 0,2,6)

        ###
        self.prevTest = QPushButton("Previous");
        self.prevTest.clicked.connect(lambda:self.moveToPrevTest())
        self.nextTest = QPushButton("Next");
        self.nextTest.clicked.connect(lambda:self.moveToNextTest())
        grid.addWidget(self.prevTest, 9, 1)
        grid.addWidget(self.nextTest, 9, 2)


        ###
        self.annotateMore = QPushButton("More annotation")
        self.annotateMore.clicked.connect(lambda:self.annotateTestFurther())
        grid.addWidget(self.annotateMore, 5, 2)

        self.revTest = QPushButton("Revert")
        self.revTest.clicked.connect(lambda:self.revertTest())
        grid.addWidget(self.revTest, 6, 2)

        ###
        self.requestNextB = QPushButton('Get Next')
        self.requestNextB.clicked.connect(lambda:self.requestNext())
        grid.addWidget(self.requestNextB, 4, 0)

        ###
        self.pageImg = QLabel()
        grid.addWidget(self.pageImg, 2,7,20,20)

        ###
        self.annotate = QPushButton("Annotate\t && request next")
        self.annotate.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.annotate.clicked.connect(lambda:self.annotateTest())
        grid.addWidget(self.annotate, 5, 0,2,2)

        ###
        self.setLayout(grid)
        self.setWindowTitle('Grader')
        self.show()
        self.requestNextB.setFocus()

loop = asyncio.get_event_loop()
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

app = QApplication(sys.argv)

serverDetails = StartUpMarkerWidget(); serverDetails.exec_()
userName, password, pageGroup, version, server, message_port, webdav_port = serverDetails.getValues()

gr = Grader(userName, password, pageGroup, version)

app.exec_()
loop.close()
