import sys
import os
import json
import asyncio
import ssl

from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext
mlpctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QAbstractItemView, QAbstractScrollArea, QApplication, QDialog, QGridLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QWidget

serverInfo = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}


def getServerInfo():
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open('../resources/serverDetails.json') as data_file:
            serverInfo = json.load(data_file)


class SimpleMessage(QMessageBox):
    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
loop = asyncio.get_event_loop()


async def handle_user_reload(server, message_port, password):
    reader, writer = await asyncio.open_connection(server, message_port, loop=loop, ssl=sslContext)
    jm = json.dumps(['RUSR', password])
    writer.write(jm.encode())
    writer.write(b'\x00')
    await writer.drain()

    data = await reader.read(100)
    terminate = data.endswith(b'\x00')
    data = data.rstrip(b'\x00')
    rmesg = json.loads(data.decode())  # message should be a list [cmd, user, arg1, arg2, etc]
    writer.close()
    return rmesg


def requestUserReload(server, message_port, password):
    rmsg = loop.run_until_complete(handle_user_reload(server, message_port, password))
    return(rmsg)


class ManagerDialog(QDialog):
    def __init__(self):
        super(ManagerDialog, self).__init__()
        self.name = "Manager"
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Please enter manager password")
        self.pwL = QLabel("Password:")
        self.pwL2 = QLabel("and again:")
        self.pwLE = QLineEdit("")
        self.pwLE.setEchoMode(QLineEdit.Password)
        self.pwLE2 = QLineEdit("")
        self.pwLE2.setEchoMode(QLineEdit.Password)
        self.okB = QPushButton('Accept')
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton('Cancel')
        self.cnB.clicked.connect(self.reject)

        grid = QGridLayout()
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.okB, 4, 3)
        grid.addWidget(self.cnB, 4, 1)

        self.setLayout(grid)
        self.show()

    def validate(self):
        if (len(self.pwLE.text()) < 4) or (self.pwLE.text() != self.pwLE2.text()):
            self.pwLE.clear()
            self.pwLE2.clear()
            return
        self.accept()

    def getNamePassword(self):
        self.pwd = self.pwLE.text()
        return(['Manager', self.pwd])


class UserDialog(QDialog):
    def __init__(self):
        super(UserDialog, self).__init__()
        self.name = ""
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Please enter user")
        self.userL = QLabel("Username:")
        self.pwL = QLabel("Password:")
        self.pwL2 = QLabel("and again:")
        self.userLE = QLineEdit("")
        self.pwLE = QLineEdit("")
        self.pwLE.setEchoMode(QLineEdit.Password)
        self.pwLE2 = QLineEdit("")
        self.pwLE2.setEchoMode(QLineEdit.Password)
        self.okB = QPushButton('Accept')
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton('Cancel')
        self.cnB.clicked.connect(self.reject)

        grid = QGridLayout()
        grid.addWidget(self.userL, 1, 1)
        grid.addWidget(self.userLE, 1, 2)
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.okB, 4, 3)
        grid.addWidget(self.cnB, 4, 1)

        self.setLayout(grid)
        self.show()

    def validate(self):
        if (len(self.pwLE.text()) < 4) or (self.pwLE.text() != self.pwLE2.text()):
            self.pwLE.clear()
            self.pwLE2.clear()
            return
        if not self.userLE.text().isalpha():
            self.userLE.clear()
            return
        self.accept()

    def getNamePassword(self):
        self.name = self.userLE.text()
        self.pwd = self.pwLE.text()
        return [self.name, self.pwd]


class userManager(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.users = {}
        self.initUI()
        self.updateGeometry()
        self.setMinimumSize(QSize(400, 500))

    def loadUserList(self):
        if(os.path.exists("../resources/userList.json")):
            with open('../resources/userList.json') as data_file:
                self.users = json.load(data_file)
                print("Users = {}".format(self.users))
        else:
            self.users = {}

    def saveUsers(self):
        fh = open("../resources/userList.json", 'w')
        fh.write(json.dumps(self.users, indent=2))
        fh.close()

    def refreshUserList(self):
        self.loadUserList()
        self.userT.clearContents()
        self.userT.setRowCount(len(self.users))
        r = 0
        for u in sorted(self.users.keys()):
            self.userT.setItem(r, 0, QTableWidgetItem(u))
            self.userT.setItem(r, 1, QTableWidgetItem(self.users[u]))
            r += 1
        self.userT.update()

    def initUI(self):
        grid = QGridLayout()

        self.userT = QTableWidget()
        self.userT.setColumnCount(2)
        self.userT.setHorizontalHeaderLabels(['Username', 'Hashed Password'])
        self.userT.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.userT.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.userT.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.refreshUserList()
        self.userT.adjustSize()
        self.userT.horizontalHeader().setStretchLastSection(True)
        grid.addWidget(self.userT, 1, 1, 4, 4)

        self.addB = QPushButton("manager setup")
        self.addB.clicked.connect(lambda: self.setManager())
        grid.addWidget(self.addB, 6, 2)

        self.addB = QPushButton("add user")
        self.addB.clicked.connect(lambda: self.addUser())
        grid.addWidget(self.addB, 7, 2)

        self.delB = QPushButton("delete user")
        self.delB.clicked.connect(lambda: self.delUser())
        grid.addWidget(self.delB, 7, 3)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(lambda: self.close())
        grid.addWidget(self.closeB, 7, 99)

        self.urB = QPushButton("RequestReload")
        self.urB.clicked.connect(self.contactServerReload)
        grid.addWidget(self.urB, 7, 4)

        self.setLayout(grid)
        self.setWindowTitle('User list')
        self.show()

    def setManager(self):
        tmp = ManagerDialog()
        if tmp.exec_() == 1:
            np = tmp.getNamePassword()
            self.users.update({np[0]: mlpctx.encrypt(np[1])})
            self.saveUsers()
            self.refreshUserList()

    def addUser(self):
        tmp = UserDialog()
        if tmp.exec_() == 1:
            np = tmp.getNamePassword()
            self.users.update({np[0]: mlpctx.encrypt(np[1])})
            self.saveUsers()
            self.refreshUserList()
            self.contactServerReload()

    def delUser(self):
        r = self.userT.currentRow()
        if r is None:
            return
        usr = self.userT.item(r, 0).text()
        tmp = SimpleMessage("Confirm delete user {}".format(usr))
        if tmp.exec_() == QMessageBox.Yes:
            del self.users[usr]
            self.saveUsers()
            self.refreshUserList()
            self.contactServerReload()

    def contactServerReload(self):
        global serverInfo
        tmp = SimpleMessage("Contact server to reload users?")
        if tmp.exec_() == QMessageBox.Yes:
            pwd, ok = QInputDialog.getText(self, "Authenticate", "Enter manager password", QLineEdit.Password)
            if ok:
                requestUserReload(serverInfo['server'], serverInfo['mport'], pwd)


def main():
    getServerInfo()
    app = QApplication(sys.argv)
    iic = userManager()
    app.exec_()


if __name__ == '__main__':
    main()
