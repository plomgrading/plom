__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

import csv
import json
import os
import sys
import pandas
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget
from ui_server_setup import Ui_ServerInfo

# TODO: move this function out of finishing... TO WHERE?
#sys.path.append("..")
#from finishing.return_tools import import_canvas_csv
# This import didn't work (because it depends on finishing/utils.py)
#
# TODO: as a workaorund we copy-paste the entire function here:
def import_canvas_csv(canvas_fromfile):
    df = pandas.read_csv(canvas_fromfile, dtype='object')
    print('Loading from Canvas csv file: "{0}"'.format(canvas_fromfile))

    # TODO: talk to @andrewr about "SIS User ID" versus "Student Number"
    cols = ['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', 'Student Number']
    assert all([c in df.columns for c in cols]), "CSV file missing columns?  We need:\n  " + str(cols)

    print('Carefully filtering rows w/o "Student Number" including:\n'
          '  almost blank rows, "Points Possible" and "Test Student"s')
    isbad = df.apply(
        lambda x: (pandas.isnull(x['Student Number']) and
                   (pandas.isnull(x['Student'])
                    or x['Student'].strip().lower().startswith('points possible')
                    or x['Student'].strip().lower().startswith('test student'))),
        axis=1)
    df = df[isbad == False]

    return df


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
            with open("../resources/serverDetails.json") as data_file:
                self.info = json.load(data_file)
        else:
            # set server address, message port and webdav port.
            self.info = {"server": "127.0.0.1", "mport": 41984, "wport": 41985}

    def putInfoIntoUi(self):
        """Grab the values from the info dict and put into the UI fields
        """
        self.ui.serverLE.setText(self.info["server"])
        self.ui.mportSB.setValue(self.info["mport"])
        self.ui.wportSB.setValue(self.info["wport"])

    def saveAndClose(self):
        """Grab values from the UI, put into dictionary and save as json.
        Then close.
        """
        self.info["server"] = self.ui.serverLE.text()
        self.info["mport"] = self.ui.mportSB.value()
        self.info["wport"] = self.ui.wportSB.value()

        fh = open("../resources/serverDetails.json", "w")
        fh.write(json.dumps(self.info, indent=4, sort_keys=True))
        fh.close()
        self.close()

    def manageUsers(self):
        """Fire up the user manager app."""
        os.system("python3 ./userManager.py")

    def getClassList(self):
        """Grab the classlist from a csv file. It must contain student numbers, family name
        and given name. The headers must be 'id', 'surname', 'name'.  Alternatively, a
        csv file exported from Canvas can be provided.
        """
        # Pop up a message box with instructions
        QMessageBox.question(
            self,
            "Class list format",
            "Class list must be a CSV with column" ' headers "id", "surname", "name".'
            '\nAlternatively, give csv exported from Canvas.',
            QMessageBox.Ok,
        )
        # Pop up a file dialog to pick a .csv
        fname = QFileDialog.getOpenFileName(
            self, "Choose class list csv", "./", "CSV files (*.csv)"
        )[0]
        # If a filename is returned then read the file.
        if fname:
            with open(fname) as csvfile:
                reader = csv.DictReader(csvfile, skipinitialspace=True)
                fields = reader.fieldnames
            print("Class list headers = {}".format(fields))

            # First check if this is Canvas output
            if all(x in fields for x in ("Student", "ID", "SIS User ID", "SIS Login ID")):
                print("This looks like it was exported from Canvas")
                df = import_canvas_csv(fname)
                print("Extracting columns from Canvas data and renaming")
                df = df[["Student Number", "Student", "Student"]]
                df.columns = ["id", "surname", "name"]
                print("Saving to classlist.csv")
                df.to_csv("../resources/classlist.csv", index=False)
                return

            # If each required header is there print a message to user.
            for hd in ["id", "surname", "name"]:
                if hd in fields:
                    print("{} is present".format(hd))
                else:
                    # Otherwise popup a warning and return.
                    QMessageBox.question(
                        self,
                        "Class list header error",
                        'The field "{}" is not present in the csv file.'.format(hd),
                        QMessageBox.Ok,
                    )
                    return
            # Copy the csv into place.
            os.system("cp {} ../resources/classlist.csv".format(fname))


app = QApplication(sys.argv)
window = SetUp()
window.show()
rv = app.exec_()
sys.exit(rv)
