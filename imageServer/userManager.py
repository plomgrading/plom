__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import requests
import json
import os
import random
import ssl
import sys

# Grab required Qt stuff
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QCheckBox,
    QDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

# Stuff for hashing and verifying passwords
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext

# Fire up password stuff
mlpctx = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
# SSL stuff for communicating with server.
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server info defaults
serverInfo = {"server": "127.0.0.1", "mport": 41984}

from aliceBob import simplePassword, makeRandomUserList, makeNumberedUserList

authSession = requests.Session()
authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))


def requestUserReload(server, port, password):
    """Get message handler to send user reload request."""
    try:
        response = authSession.put(
            "https://{}:{}/admin/reloadUsers".format(server, port),
            json={"pw": password},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            return False
        else:
            raise Exception(
                "Something nasty has happened. Got return code = {}".format(
                    response.status_code
                )
            )
    except Exception as err:
        print(err)
        return False

    return True


class CannedUserList(QDialog):
    def __init__(self, lst):
        super(CannedUserList, self).__init__()
        self.npList = lst
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Which users do you want to add?")
        self.okB = QPushButton("Accept")
        self.okB.clicked.connect(self.accept)
        self.cnB = QPushButton("Cancel")
        self.cnB.clicked.connect(self.reject)
        self.userList = QTableWidget()
        self.howManyL = QLabel("Add how many?")
        self.howManySB = QSpinBox()
        self.setList()

        grid = QGridLayout()
        grid.addWidget(self.userList, 1, 1, 3, 3)
        grid.addWidget(self.howManyL, 4, 1)
        grid.addWidget(self.howManySB, 4, 2)
        grid.addWidget(self.okB, 6, 3)
        grid.addWidget(self.cnB, 6, 1)

        self.setLayout(grid)
        self.show()

    def setList(self):
        self.userList.setColumnCount(2)
        self.userList.setHorizontalHeaderLabels(["User", "Password"])
        for (n, p) in self.npList:
            r = self.userList.rowCount()
            self.userList.insertRow(r)
            self.userList.setItem(r, 0, QTableWidgetItem(n))
            self.userList.setItem(r, 1, QTableWidgetItem(p))
        self.userList.resizeColumnsToContents()
        self.userList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.userList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.howManySB.setMaximum(len(self.npList))


def getServerInfo():
    """Get server details from json file"""
    global serverInfo
    if os.path.isfile("../resources/serverDetails.json"):
        with open("../resources/serverDetails.json") as data_file:
            serverInfo = json.load(data_file)


class ErrorMessage(QMessageBox):
    """A simple error message pop-up"""

    def __init__(self, txt):
        super(ErrorMessage, self).__init__()
        fnt = self.font()
        fnt.setPointSize((fnt.pointSize() * 3) // 2)
        self.setFont(fnt)
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Ok)


class SimpleMessage(QMessageBox):
    """Very simple messagebox with yes/no buttons"""

    def __init__(self, txt):
        super(SimpleMessage, self).__init__()
        self.setText(txt)
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)


class ManagerDialog(QDialog):
    """Simple dialog to set manager password"""

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
        self.okB = QPushButton("Accept")
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton("Cancel")
        self.cnB.clicked.connect(self.reject)

        grid = QGridLayout()
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.okB, 4, 3)

        self.setLayout(grid)
        self.show()

    def validate(self):
        """Check that password is at least 4 char long
        and that the two passwords match.
        If all good then accept
        else clear the two password lineedits.
        """
        if (len(self.pwLE.text()) < 4) or (self.pwLE.text() != self.pwLE2.text()):
            self.pwLE.clear()
            self.pwLE2.clear()
            return
        self.accept()

    def getNamePassword(self):
        """Return [Manager, manager password]"""
        self.pwd = self.pwLE.text()
        return ["Manager", self.pwd]


class UserDialog(QDialog):
    """Simple dialog to enter username and password"""

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
        initialpw = simplePassword()
        self.pwLE = QLineEdit(initialpw)
        # self.pwLE.setEchoMode(QLineEdit.Password)
        self.pwLE2 = QLineEdit(initialpw)
        self.pwLE2.setEchoMode(QLineEdit.Password)
        self.okB = QPushButton("Accept")
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton("Cancel")
        self.cnB.clicked.connect(self.reject)

        self.pwCB = QCheckBox("(hide/show)")
        self.pwCB.setCheckState(Qt.Unchecked)
        self.pwCB.stateChanged.connect(self.togglePWShow)

        grid = QGridLayout()
        grid.addWidget(self.userL, 1, 1)
        grid.addWidget(self.userLE, 1, 2)
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwCB, 2, 3)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.okB, 4, 3)
        grid.addWidget(self.cnB, 4, 1)

        self.setLayout(grid)
        self.show()

    def togglePWShow(self):
        if self.pwCB.checkState() == Qt.Checked:
            self.pwLE.setEchoMode(QLineEdit.Password)
        else:
            self.pwLE.setEchoMode(QLineEdit.Normal)

    def validate(self):
        """Check that password is at least 4 char long
        and that the two passwords match.
        If all good then accept
        else clear the two password lineedits.
        """
        if (len(self.pwLE.text()) < 4) or (self.pwLE.text() != self.pwLE2.text()):
            self.pwLE.clear()
            self.pwLE2.clear()
            return
        if not self.userLE.text().isalpha():
            self.userLE.clear()
            return
        self.accept()

    def getNamePassword(self):
        """Return [username, password]"""
        self.name = self.userLE.text()
        self.pwd = self.pwLE.text()
        return [self.name, self.pwd]


class userManager(QWidget):
    """Simple user manager window which lists the set of users"""

    def __init__(self):
        QWidget.__init__(self)
        # dictionary for user list [user: hashedPassword]
        self.users = {}
        self.initUI()
        self.updateGeometry()
        self.setMinimumSize(QSize(400, 500))
        self.move(100, 100)

    def loadUserList(self):
        """Load the userlist from json"""
        # If the file is there load it, else set user list to {}
        # Json is dict of [user: hashedPassword]
        if os.path.exists("../resources/userList.json"):
            with open("../resources/userList.json") as data_file:
                self.users = json.load(data_file)
        else:
            self.users = {}

    def saveUsers(self):
        """Save the user list to json file"""
        fh = open("../resources/userList.json", "w")
        fh.write(json.dumps(self.users, indent=2))
        fh.close()

    def refreshUserList(self):
        """Reload the list of users, clear table and repopulate it"""
        # Load the users
        self.loadUserList()
        # Clear the table
        self.userT.clearContents()
        # Set number of rows in table to length of user list
        self.userT.setRowCount(len(self.users))
        # Populate the table.
        r = 0
        for u in sorted(self.users.keys()):
            self.userT.setItem(r, 0, QTableWidgetItem(u))
            self.userT.setItem(r, 1, QTableWidgetItem(self.users[u]))
            r += 1
        # force update of table.
        self.userT.update()

    def initUI(self):
        grid = QGridLayout()

        self.userT = QTableWidget()
        self.userT.setColumnCount(2)
        self.userT.setHorizontalHeaderLabels(["Username", "Hashed Password"])
        self.userT.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.userT.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.userT.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.refreshUserList()
        self.userT.adjustSize()
        self.userT.horizontalHeader().setStretchLastSection(True)
        grid.addWidget(self.userT, 1, 1, 4, 4)

        self.addB = QPushButton("manager setup")
        self.addB.clicked.connect(lambda: self.setManager())
        grid.addWidget(self.addB, 6, 1)

        self.addB = QPushButton("add user")
        self.addB.clicked.connect(lambda: self.addUser())
        grid.addWidget(self.addB, 7, 2)

        self.delB = QPushButton("delete user")
        self.delB.clicked.connect(lambda: self.delUser())
        grid.addWidget(self.delB, 7, 3)

        self.closeB = QPushButton("close")
        self.closeB.clicked.connect(lambda: self.reloadAndClose())
        grid.addWidget(self.closeB, 7, 99)

        self.urB = QPushButton("RequestReload")
        self.urB.clicked.connect(self.contactServerReload)
        grid.addWidget(self.urB, 7, 4)

        self.addB = QPushButton("build canned users")
        self.addB.clicked.connect(lambda: self.buildCannedUsers())
        grid.addWidget(self.addB, 7, 1)

        self.setLayout(grid)
        self.setWindowTitle("User list")
        self.show()

    def setManager(self):
        """Set the manager password"""
        tmp = ManagerDialog()
        if tmp.exec_() == 1:
            # If dialog accepted then encrypt password
            # add manager to list, save and refresh list.
            np = tmp.getNamePassword()
            self.users.update({np[0]: mlpctx.encrypt(np[1])})
            self.saveUsers()
            self.refreshUserList()

    def addUser(self):
        """Add a user"""
        tmp = UserDialog()
        if tmp.exec_() == 1:
            # If dialog accepted then encrypt password
            # add user to list, save and refresh list.
            np = tmp.getNamePassword()
            self.users.update({np[0]: mlpctx.encrypt(np[1])})
            self.saveUsers()
            self.refreshUserList()

    def delUser(self):
        """Delete the currently selected user"""
        # Grab current row
        r = self.userT.currentRow()
        if r is None:
            return
        # Get username from row, and ask for confirmation
        usr = self.userT.item(r, 0).text()
        tmp = SimpleMessage("Confirm delete user {}".format(usr))
        if tmp.exec_() == QMessageBox.Yes:
            # delete the user, save, and refresh.
            del self.users[usr]
            self.saveUsers()
            self.refreshUserList()

    def reloadAndClose(self):
        """Popup message asking if user wants to reload before
        closing.
        """
        self.contactServerReload()
        self.close()

    def contactServerReload(self):
        """Popup message to confirm sending reload request"""
        global serverInfo
        tmp = SimpleMessage("Contact server to reload users?")
        if tmp.exec_() == QMessageBox.Yes:
            pwd, ok = QInputDialog.getText(
                self, "Authenticate", "Enter manager password", QLineEdit.Password
            )
            if ok:
                # Fire off reload request
                ret = requestUserReload(serverInfo["server"], serverInfo["mport"], pwd)
                if not ret:
                    msg = ErrorMessage("Something went wrong when contacting server.")
                    msg.exec_()

    def buildCannedUsers(self):
        # get canned user list
        # TODO: make this chooesable somehow
        # lst = makeRandomUserList()
        lst = makeNumberedUserList()
        # uncomment the below to shuffle list into random order
        # random.shuffle(lst)
        tmp = CannedUserList(lst)
        if tmp.exec_() != QDialog.Accepted:
            return

        doList = lst[: tmp.howManySB.value()]
        with open("../resources/cannedUserList.txt", "a+") as fh:
            for (n, p) in doList:
                if n not in self.users:
                    self.users.update({n: mlpctx.encrypt(p)})
                    fh.write("{}\t{}\n".format(n, p))
                else:
                    print("User {} already present".format(n))
        self.saveUsers()
        self.refreshUserList()


def main():
    getServerInfo()
    app = QApplication(sys.argv)
    iic = userManager()
    app.exec_()


if __name__ == "__main__":
    main()
