import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QStyleFactory, QWidget

from ui_server_setup import Ui_ServerInfo

class SetUp(QWidget):
    def __init__(self):
        super(SetUp, self).__init__()
        self.ui = Ui_ServerInfo()
        self.ui.setupUi(self)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.manageUsersButton.clicked.connect(self.manageUsers)
        self.ui.saveCloseButton.clicked.connect(self.saveAndClose)

        self.info = {}
        self.getServerInfo()
        self.putInfoIntoUi()

    def getServerInfo(self):
        if os.path.isfile("../resources/serverDetails.json"):
            with open('../resources/serverDetails.json') as data_file:
                self.info = json.load(data_file)
        else:
            self.info = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}

    def putInfoIntoUi(self):
        self.ui.serverLE.setText(self.info['server'])
        self.ui.mportSB.setValue(self.info['mport'])
        self.ui.wportSB.setValue(self.info['wport'])

    def saveAndClose(self):
        self.info['server'] = self.ui.serverLE.text()
        self.info['mport'] = self.ui.mportSB.value()
        self.info['wport'] = self.ui.wportSB.value()

        fh = open("../resources/serverDetails.json", 'w')
        fh.write(json.dumps(self.info, indent=4, sort_keys=True))
        fh.close()
        self.close()

    def manageUsers(self):
        os.system('python3 ./userManager.py')


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create("Fusion"))

window = SetUp()
window.show()
rv = app.exec_()
sys.exit(rv)
