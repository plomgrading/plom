import os, sys, argparse, tempfile, json
from collections import defaultdict

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtSql import *

from examviewwindow import examViewWindow
import ssl
import asyncio

server = 'localhost'
webdav_port=41985
message_port=41984

# # # # # # # # # # # #
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# # # # # # # # # # # #

async def handle_messaging(msg):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
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
    return(rmesg)

def SRMsg(msg):
    # print("Sending message {}",format(msg))
    rmsg = loop.run_until_complete(handle_messaging(msg))
    if( rmsg[0] == 'ACK'):
        return(rmsg)
    elif( rmsg[0] == 'ERR'):
        # print("Some sort of error occurred - didnt get an ACK, instead got ", rmsg)
        msg = errorMessage(rmsg[1])
        msg.exec_()
        return(rmsg)
    else:
        msg = errorMessage("Something really wrong has happened.")
        self.Close()

class errorMessage(QMessageBox):
  def __init__(self, txt):
    super(QMessageBox, self).__init__()
    self.setText(txt)
    self.setStandardButtons(QMessageBox.Ok)

class userListDialog(QDialog):
    def __init__(self, userList):
        super(userListDialog, self).__init__()
        self.uList=sorted(userList)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Current Users")
        self.userLW=QListWidget()
        for name in self.uList:
            self.userLW.addItem(name)

        self.okB = QPushButton('Okay')
        self.okB.clicked.connect(self.accept)

        grid = QGridLayout()
        grid.addWidget(self.userLW,1,1)
        grid.addWidget(self.okB,2,2)

        self.setLayout(grid)
        self.show()


class userDialog(QDialog):
    def __init__(self):
        super(userDialog, self).__init__()
        self.name=""
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Please enter user")
        self.userL = QLabel("User name to add:")

        self.userLE = QLineEdit("")

        self.okB = QPushButton('Accept')
        self.okB.clicked.connect(self.accept)
        self.cnB = QPushButton('Cancel')
        self.cnB.clicked.connect(self.reject)

        grid = QGridLayout()
        grid.addWidget(self.userL,1,1)
        grid.addWidget(self.userLE,1,2)
        grid.addWidget(self.okB,4,3)
        grid.addWidget(self.cnB,4,1)

        self.setLayout(grid)
        self.show()

    def getName(self):
        self.name=self.userLE.text()
        return(self.name)

class userProgress(QDialog):
    def __init__(self, counts):
        QDialog.__init__(self)
        self.setModal(True)
        grid = QGridLayout()

        self.ptab = QTableWidget(len(counts)+1, 3)
        self.ptab.setHorizontalHeaderLabels(['User','Done','Progress'])
        grid.addWidget(self.ptab,1,1)

        gb={}
        r=1; mx=0; doneTotal=0
        for k in counts.keys():
            if(counts[k][0]>mx):
                mx=counts[k][0]

        for k in counts.keys():
            gb[k] = QProgressBar(); gb[k].setMaximum(mx);  gb[k].setValue(counts[k][0]); gb[k].setFormat("%v")
            self.ptab.setItem(r,0,QTableWidgetItem(str(k)))
            self.ptab.setItem(r,1,QTableWidgetItem(str( counts[k][0])))
            self.ptab.setCellWidget(r,2,gb[k])
            doneTotal += counts[k][0]
            r+=1
        self.ptab.setItem(0,0,QTableWidgetItem('All'))
        self.ptab.setItem(0,1,QTableWidgetItem(str(doneTotal)))

        self.ptab.resizeColumnsToContents()
        self.ptab.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.ptab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ptab.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.closeB =QPushButton("close")
        self.closeB.clicked.connect(lambda: self.close())
        grid.addWidget(self.closeB, 99,99)
        self.setLayout(grid)
        self.show()

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
        self.title=txt
        self.addItem(txt)

class examTable(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName('../resources/identity.db')
        self.db.setHostName("Andrew")
        self.db.open()
        self.initUI();
        self.loadData()
        self.setFilterOptions()

    def initUI(self):
        grid = QGridLayout()
        self.exM = QSqlTableModel(self,self.db)
        self.exM.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.exM.setTable("idimage")
        self.exV = simpleTableView(self.exM)

        grid.addWidget(self.exV,0,0,4,7)

        self.filterGo=QPushButton("Filter Now")
        self.filterGo.clicked.connect(lambda: self.filter())
        grid.addWidget(self.filterGo,5,0)
        self.flU=filterComboBox("Marker"); grid.addWidget(self.flU,5,2)
        self.flS=filterComboBox("Status"); grid.addWidget(self.flS,5,3)

        self.uprogB = QPushButton("User progress")
        self.uprogB.clicked.connect(lambda: self.computeUserProgress())
        grid.addWidget(self.uprogB, 3,8)

        self.pgImg = examViewWindow()
        grid.addWidget(self.pgImg, 0,10,20,20)

        self.setLayout(grid)
        self.show()

    def requestPageImage(self, index):
        rec = self.exM.record( index.row() )
        self.pgImg.updateImage("../scanAndGroup/readyForGrading/idgroup/{}.png".format(rec.value('tgv')))

    def computeUserProgress(self):
        ustats = defaultdict(lambda: [0,0])
        for r in range( self.exM.rowCount() ):
            if( self.exM.record(r).value('user') == 'None' ):
                continue
            ustats[ self.exM.record(r).value('user') ][0]+=1
            if(self.exM.record(r).value('status')=='Identified'):
                ustats[ self.exM.record(r).value('user') ][1]+=1
        tmp = userProgress(ustats)

    def getUniqueFromColumn(self,col):
        lst=set()
        query = QSqlQuery(db=self.db)
        query.exec_("select {} from exam".format(col))
        while(query.next()):
            lst.add( str(query.value(0)))
        return( sorted(list(lst)) )

    def loadData(self):
        #self.doQueryAndRemoveColumns("select * from exam")
        for c in [0,1]:
            self.exV.hideColumn(c)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    def setFilterOptions(self):
        self.flS.insertItems( 1, self.getUniqueFromColumn('status') )
        self.flU.insertItems( 1, self.getUniqueFromColumn('user') )

    def filter(self):
        flt = []
        if(self.flS.currentText()!='Status'):
            flt.append('status=\'{}\''.format(self.flS.currentText()))
        if(self.flU.currentText()!='Marker'):
            flt.append('user=\'{}\''.format(self.flU.currentText()))

        if(len(flt)>0):
            flts =  " AND ".join(flt)
        else:
            flts = ""
        self.exM.setFilter(flts)
        self.exV.resizeColumnsToContents()
        self.exV.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)


class manager(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.initUI();

    # def addUser(self):
    #     tmp = userDialog()
    #     if( tmp.exec_() == 1):
    #         msg = SRMsg(['ZAU', tmp.getName()])
    #     else:
    #         return
    # def listUsers(self):
    #     msg = SRMsg(['ZLU'])
    #     tmp = userListDialog(msg[1])
    #     tmp.exec_()

    def initUI(self):
        grid = QGridLayout()
        self.extb=examTable()

        grid.addWidget(self.extb,1,1,4,6)

        # self.listB = QPushButton("list users")
        # self.listB.clicked.connect(lambda: self.listUsers())
        # grid.addWidget(self.listB,6,1)
        #
        # self.addB = QPushButton("add user")
        # self.addB.clicked.connect(lambda: self.addUser())
        # grid.addWidget(self.addB,6,2)

        self.closeB=QPushButton("close")
        self.closeB.clicked.connect(lambda: self.close())
        grid.addWidget(self.closeB,6,99)

        self.setLayout(grid)
        self.setWindowTitle('Where we are at.')
        self.show()

loop = asyncio.get_event_loop()
tempDirectory = tempfile.TemporaryDirectory()
directoryPath = tempDirectory.name

app = QApplication(sys.argv)
iic = manager()
app.exec_()
loop.close()
