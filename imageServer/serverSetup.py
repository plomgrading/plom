import csv
import json
import os
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget
from ui_server_setup import Ui_ServerInfo


class SetUp(QWidget):
    def __init__(self):
        """Init the UI and connect buttons to the relevant functions
        """
        super(SetUp, self).__init__()
        self.ui = Ui_ServerInfo()
        self.ui.setupUi(self)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.manageUsersButton.clicked.connect(self.manageUsers)
        self.ui.saveCloseButton.clicked.connect(self.saveAndClose)
        self.ui.classListButton.clicked.connect(self.getClassList)
        # Make a dictionary for storing server info which gets saved as json.
        self.info = {}
        self.getServerInfo()
        self.putInfoIntoUi()

    def getServerInfo(self):
        """Read the server info from file if it exists, else set to sensible
        default values.
        """
        if os.path.isfile("../resources/serverDetails.json"):
            with open('../resources/serverDetails.json') as data_file:
                self.info = json.load(data_file)
        else:
            # set server address, message port and webdav port.
            self.info = {'server': '127.0.0.1', 'mport': 41984, 'wport': 41985}

    def putInfoIntoUi(self):
        """Grab the values from the info dict and put into the UI fields
        """
        self.ui.serverLE.setText(self.info['server'])
        self.ui.mportSB.setValue(self.info['mport'])
        self.ui.wportSB.setValue(self.info['wport'])

    def saveAndClose(self):
        """Grab values from the UI, put into dictionary and save as json.
        Then close.
        """
        self.info['server'] = self.ui.serverLE.text()
        self.info['mport'] = self.ui.mportSB.value()
        self.info['wport'] = self.ui.wportSB.value()

        fh = open("../resources/serverDetails.json", 'w')
        fh.write(json.dumps(self.info, indent=4, sort_keys=True))
        fh.close()
        self.close()

    def manageUsers(self):
        """Fire up the user manager app."""
        os.system('python3 ./userManager.py')

    def getClassList(self):
        """Grab the classlist from a csv file. It must contain student numbers, family name
        and given name. The headers must be 'id', 'surname', 'name'
        """
        # Pop up a message box with instructions
        QMessageBox.question(self, "Class list format",
                             "Class list must be a CSV with column"
                             " headers \"id\", \"surname\", \"name\".",
                             QMessageBox.Ok)
        # Pop up a file dialog to pick a .csv
        fname = QFileDialog.getOpenFileName(self,  'Choose class list csv',
                                            './', 'CSV files (*.csv)')[0]
        # If a filename is returned then read the file.
        if fname:
            with open(fname) as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                print("Class list headers = {}".format(reader.fieldnames))
                # If each required header is there print a message to user.
                for hd in ['id', 'surname', 'name']:
                    if hd in reader.fieldnames:
                        print("{} is present".format(hd))
                    else:
                        # Otherwise popup a warning and return.
                        QMessageBox.question(self, "Class list header error",
                                             "The field \"{}\" is not present in the csv file.".format(hd),
                                             QMessageBox.Ok)
                        return
            # Copy the csv into place.
            os.system("cp {} ../resources/classlist.csv".format(fname))


app = QApplication(sys.argv)
window = SetUp()
window.show()
rv = app.exec_()
sys.exit(rv)
