import sys
import os
import json
import csv
from PyQt5.QtWidgets import QApplication, QStyleFactory, QWidget, QFileDialog, QMessageBox
from ui_server_setup import Ui_ServerInfo


class SetUp(QWidget):
    def __init__(self):
        super(SetUp, self).__init__()
        self.ui = Ui_ServerInfo()
        self.ui.setupUi(self)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.manageUsersButton.clicked.connect(self.manageUsers)
        self.ui.saveCloseButton.clicked.connect(self.saveAndClose)
        self.ui.classListButton.clicked.connect(self.getClassList)
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

    def getClassList(self):
        QMessageBox.question(self, "Class list format", "Class list must be a CSV with column headers \"id\", \"surname\", \"name\" and optionally \"code\".", QMessageBox.Ok)
        fname = QFileDialog.getOpenFileName(self,  'Choose class list csv', './', 'CSV files (*.csv)')[0]
        if fname:
            with open(fname) as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                print("Class list headers = {}".format(reader.fieldnames))

                for hd in ['id', 'surname', 'name']:
                    if hd in reader.fieldnames:
                        print("{} is present".format(hd))
                    else:
                        QMessageBox.question(self, "Class list header error", "The field \"{}\" is not present in the csv file.".format(hd), QMessageBox.Ok)
                        return
            os.system("cp {} ../resources/classlist.csv".format(fname))


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create("Fusion"))

window = SetUp()
window.show()
rv = app.exec_()
sys.exit(rv)
