from examviewwindow import examViewWindow
from gui_utils import *

import os, sys, tempfile, json

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import csv
from collections import defaultdict
import easywebdav2
import asyncio
import ssl

webdav_user = 'hack'
webdav_passwd = 'duhbah'
server = 'localhost'
webdav_port=41985
message_port=41984

# # # # # # # # # # # #
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# # # # # # # # # # # #

###

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
        print( [self.prefix, self.status, self.sid, self.sname, self.originalFile])

    def setStatus(self, st):
        self.status = st

    def setReverted(self):
        self.status="unidentified"
        self.sid="-1"
        self.sname="unknown"

    def setID(self, sid, sname):
        #tgv = t0000p00v0
        #... = 0123456789
        self.status = "identified"
        self.sid = sid
        self.sname=sname

def getFileDav(dfn, lfn):
  webdav = easywebdav2.connect(server, port=webdav_port, username=webdav_user, password=webdav_passwd)
  try:
    argh = webdav.download(dfn,lfn)
  except Exception as ex:
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print( message)


async def handle_messaging(msg):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    print("Sending message {}".format(msg))
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
        msg = errorMessage(rmsg[1])
        msg.exec_()
        return(rmsg)
    else:
        msg = errorMessage("Something really wrong has happened.")
        self.Close()


class examModel(QAbstractTableModel):
    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.paperList=[]
        self.header=['TestGroupVersion','Status','ID','Name']

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
            self.paperList[index.row()].sid=value
            self.dataChanged.emit(index, index)
            return True
        elif(index.column()==3):
            self.paperList[index.row()].sname=value
            self.dataChanged.emit(index, index)
            return True
        return False

    def identifyStudent(self, index, sid, sname):
        self.setData(index[1],'identified')
        self.setData(index[2],sid)
        self.setData(index[3],sname)

    def revertStudent(self, index):
        self.setData(index[1],'unidentified')
        self.setData(index[2],'')
        self.setData(index[3],'')

    def addPaper(self, rho):
        r=self.rowCount()
        self.beginInsertRows(QModelIndex(), r,r)
        self.paperList.append(rho)
        self.endInsertRows()
        return(r)

    def rowCount(self, parent=None):
        return(len(self.paperList))
    def columnCount(self, parent=None):
        return 4

    def data(self, index, role=Qt.DisplayRole):
        if( role != Qt.DisplayRole ):
            return QVariant()
        elif(index.column()==0):
            return self.paperList[index.row()].prefix
        elif(index.column()==1):
            return self.paperList[index.row()].status
        elif(index.column()==2):
            return self.paperList[index.row()].sid
        elif(index.column()==3):
            return self.paperList[index.row()].sname
        else:
            return QVariant()

    def headerData(self, c, orientation, role):
        if( role != Qt.DisplayRole ):
            return
        elif( orientation == Qt.Horizontal ):
            return(self.header[c])
        return c

class IDClient(QWidget):
  def __init__(self, userName, password):
    super(IDClient, self).__init__()
    self.userName=userName
    self.password=password
    self.requestToken()
    self.getClassList()

    self.setCompleters()
    self.paperList=[]
    self.exM = examModel()
    self.exV = QTableView()
    self.exV.setModel(self.exM)
    self.unidCount=0
    self.initUI(userName)

  def requestToken(self):
    msg = SRMsg(['AUTH', self.userName, self.password])
    if(msg[0]=='ERR'):
        errorMessage("Password problem")
        quit()
    else:
        self.token=msg[1]
        print('Token set to {}'.format(self.token))

  def getClassList(self):
      msg = SRMsg(['iRCL', self.userName, self.token])
      if(msg[0]=='ERR'):
        errorMessage("Classlist problem")
        quit()
      dfn = msg[1]
      fname= directoryPath+"/cl.csv"
      getFileDav(dfn, fname);
      # read classlist into dictionaries
      self.studentNamesToNumbers=defaultdict(int)
      self.studentNumbersToNames=defaultdict(str)
      with open(fname) as csvfile:
          reader=csv.DictReader(csvfile, skipinitialspace=True)
          for row in reader:
              sn = row['surname']+', '+row['name']
              self.studentNamesToNumbers[sn]=str(row['id'])
              self.studentNumbersToNames[str(row['id'])]=sn
      #acknowledge class list
      msg = SRMsg(['iGCL', self.userName, self.token, dfn])
      if(msg[0]=='ERR'):
        errorMessage("Classlist problem")
        quit()
      return(True)

  def setCompleters(self):
    self.sidlist=QStringListModel()
    self.snamelist=QStringListModel()

    self.sidlist.setStringList(list(self.studentNumbersToNames.keys()))
    self.snamelist.setStringList(list(self.studentNamesToNumbers.keys()))

    self.sidcompleter = QCompleter(); self.sidcompleter.setModel(self.sidlist)
    self.snamecompleter = QCompleter(); self.snamecompleter.setModel(self.snamelist)

  def selChanged(self, selnew, selold):
      self.studentID.setText( self.exM.data( selnew.indexes()[2] ) )
      self.studentName.setText(self.exM.data( selnew.indexes()[3] ) )
      self.updateImage( selnew.indexes()[0].row() )

  def updateImage(self, r=0):
    self.testImg.updateImage( self.exM.paperList[r].originalFile )

  def addPaperToList(self, paper):
      r =self.exM.addPaper(paper)
      self.exV.selectRow( r )
      self.updateImage(r)
      self.unidCount+=1

  def requestNext(self):
    # ask server for next unid'd paper >>> test,fname = server.nextUnIDd(self.userName)
    msg = SRMsg(['iNID', self.userName, self.token])
    if(msg[0]=='ERR'):
        return
    test = msg[1]; fname=msg[2]; iname=directoryPath+"/"+test+".png"
    getFileDav(fname, iname)
    self.addPaperToList( Paper(test, iname) )
    #acknowledge got test  >>>   server.gotTest(self.userName, test, fname)
    msg = SRMsg(['iGTP', self.userName, self.token, test, fname])
    self.studentID.setFocus()

  def identifyStudent(self, index, alreadyIDd=False):
      self.exM.identifyStudent(index, self.studentID.text(),self.studentName.text())
      code = self.exM.data(index[0])
      if(alreadyIDd):
          # return ID'd test >>> server.returnAlreadyIDd(self.userName, ret, self.studentID.text(), self.studentName.text())
          msg = SRMsg(['iRAD', self.userName, self.token, code, self.studentID.text(), self.studentName.text()])
      else:
          # return already ID'd test >>> server.returnIDd(self.userName, ret, self.studentID.text(), self.studentName.text())
          msg = SRMsg(['iRID', self.userName, self.token, code, self.studentID.text(), self.studentName.text()])
      if(msg[0]=='ERR'):
          self.exM.revertStudent(index)
          self.studentID.setText("")
          self.studentName.setText("")
          return(False)
      else:
          self.unidCount-=1
          return(True)

  def moveToNextUnID(self):
      rt = self.exM.rowCount()
      if(rt==0):
          return
      rstart = self.exV.selectedIndexes()[0].row()
      r = (rstart+1) %  rt
      while(self.exM.data(self.exM.index(r,2) ) == "identified" and  r != rstart):
          r = (r+1) %  rt
      self.exV.selectRow(r)

  def enterID(self):
      if(self.exM.rowCount()==0):
          return
      index = self.exV.selectedIndexes()
      code = self.exM.data(index[0] )
      if(code == None):
        return
      status = self.exM.data(index[1] )
      alreadyIDd=False

      if( status == "identified"):
        msg = simpleMessage('Do you want to change the ID?')
        if( msg.exec_() == QMessageBox.No ):
            return
        else:
            alreadyIDd=True

      if(self.studentID.text() in self.studentNumbersToNames ):
          self.studentName.setText(self.studentNumbersToNames[self.studentID.text()])
          msg = simpleMessage('Student ID {:s} = {:s}. Enter and move to next?'.format(self.studentID.text(),self.studentName.text()))
          if( msg.exec_()==QMessageBox.No ):
            return
      else:
        msg = simpleMessage('Student ID {:s} not in list. Do you want to enter it anyway?'.format(self.studentID.text()) )
        if( msg.exec_()==QMessageBox.No ):
            return
        self.studentName.setText("Unknown")

      if( self.identifyStudent(index,alreadyIDd)==True ):
          if(alreadyIDd==False and self.unidCount==0):
            self.requestNext()
          else:
            self.moveToNextUnID()

  def enterName(self):
      if(self.exM.rowCount()==0):
          return
      index = self.exV.selectedIndexes()
      code = self.exM.data(index[0] )
      if(code == None):
        return
      status = self.exM.data(index[1] )
      alreadyIDd=False

      if(status=="identified"):
        msg = simpleMessage('Do you want to change the ID?')
        if( msg.exec_()== QMessageBox.No ):
            return
        else:
            alreadyIDd=True

      if(self.studentName.text() in self.studentNamesToNumbers):
        self.studentID.setText(self.studentNamesToNumbers[self.studentName.text()])
        msg = simpleMessage( 'Student ID {:s} = {:s}. Enter and move to next?'.format(self.studentID.text(),self.studentName.text()) )
        if( msg.exec_() == QMessageBox.No ):
          return
      else:
        msg = simpleMessage( 'Student ID {:s} not in list. Do you want to enter it anyway?'.format(self.studentID.text()) )
        if( msg.exec_() == QMessageBox.No ):
          return
        self.studentName.setText("Unknown")

      self.identifyStudent(index,alreadyIDd)
      if(alreadyIDd==False and self.unidCount==0):
        self.requestNext()
      else:
        self.moveToNextUnID()

  def shutDown(self):
      self.DNF()
      msg = SRMsg(['UCL', self.userName, self.token])
      self.close()

  def DNF(self):
      rc = self.exM.rowCount()
      for r in range(rc):
          if( self.exM.data(self.exM.index(r,1) ) != "identified" ):
            msg = SRMsg(['iDNF', self.userName, self.token, self.exM.data(self.exM.index(r,0) )])

  def initUI(self,userName):
      grid = QGridLayout()

      self.nameL = QLabel('Name:')
      self.nameF = QLabel(userName)
      grid.addWidget(self.nameL, 1, 0)
      grid.addWidget(self.nameF, 1, 1)

      ###

      self.exV.setModel(self.exM)
      self.exV.setSelectionBehavior(QAbstractItemView.SelectRows)
      self.exV.setSelectionMode(QAbstractItemView.SingleSelection)
      self.exV.setEditTriggers(QAbstractItemView.NoEditTriggers)
      self.exV.selectionModel().selectionChanged.connect(self.selChanged)
      grid.addWidget(self.exV, 6, 0,2,5)

      ###
      self.testImg = examViewWindow()
      grid.addWidget(self.testImg, 2,7,20,20)


      self.SID = QLabel("Student ID")
      self.studentID = QLineEdit()
      self.studentID.setCompleter(self.sidcompleter)
      self.studentID.returnPressed.connect(lambda:self.enterID())

      self.SName = QLabel("Student Name")
      self.studentName = QLineEdit()
      self.studentName.setCompleter(self.snamecompleter)
      self.studentName.returnPressed.connect(lambda:self.enterName())

      fnt = self.studentID.font()
      fnt.setPointSize( (fnt.pointSize()*3)//2 )
      self.studentID.setFont(fnt)
      self.studentName.setFont(fnt)

      grid.addWidget(self.SID, 4, 0)
      grid.addWidget(self.SName, 5, 0)
      grid.addWidget(self.studentID, 4, 1,1,3)
      grid.addWidget(self.studentName, 5, 1,1,3)

      ###

      self.nextUnIDB = QPushButton('RequestNext')
      self.nextUnIDB.clicked.connect(lambda:self.requestNext())
      grid.addWidget(self.nextUnIDB, 8, 0)

      ###

      self.closeB = QPushButton("Close")
      self.closeB.clicked.connect(lambda:self.shutDown())
      grid.addWidget(self.closeB,100,1)
      ###

      self.setLayout(grid)
      self.setWindowTitle('Identifier')
      self.show()

loop = asyncio.get_event_loop()
def main():
    global directoryPath
    tempDirectory = tempfile.TemporaryDirectory()
    directoryPath = tempDirectory.name

    app = QApplication(sys.argv)

    serverDetails = startUpIDWidget(); serverDetails.exec_()
    userName, password, server, message_port, webdav_port = serverDetails.getValues()

    TA = IDClient(userName, password)

    sys.exit(app.exec_())
    loop.close()

if __name__ == '__main__':
    main()
