#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import csv
import json
import os
import sys
import subprocess
import pandas
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget
from ui_server_setup import Ui_ServerInfo

# TODO: move this function out of finishing... TO WHERE?
# sys.path.append("..")
# from finishing.return_tools import import_canvas_csv
# This import didn't work (because it depends on finishing/utils.py)
#
# TODO: as a workaorund we copy-paste the entire function here:
def import_canvas_csv(canvas_fromfile):
    df = pandas.read_csv(canvas_fromfile, dtype="object")
    print('Loading from Canvas csv file: "{0}"'.format(canvas_fromfile))

    # Note: Canvas idoicy whereby "SIS User ID" is same as "Student Number"
    cols = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section", "Student Number"]
    assert all(
        [c in df.columns for c in cols]
    ), "CSV file missing columns?  We need:\n  " + str(cols)

    print(
        'Carefully filtering rows w/o "Student Number" including:\n'
        '  almost blank rows, "Points Possible" and "Test Student"s'
    )
    isbad = df.apply(
        lambda x: (
            pandas.isnull(x["Student Number"])
            and (
                pandas.isnull(x["Student"])
                or x["Student"].strip().lower().startswith("points possible")
                or x["Student"].strip().lower().startswith("test student")
            )
        ),
        axis=1,
    )
    df = df[isbad == False]

    return df


def checkNonCanvasCSV(fname):
    """Read in a csv and check it has ID column.

    Must also have either
    (*) studentName column or
    (*) [surname/familyName/lastName] and [name/givenName(s)/preferredName(s)/firstName/nickName(s)] columns
    In the latter case it creates a studentName column
    """
    df = pandas.read_csv(fname, dtype="object")
    print('Loading from non-Canvas csv file: "{0}"'.format(fname))
    # strip excess whitespace from column names
    df.rename(columns=lambda x: x.strip(), inplace=True)

    # now check we have the columns needed
    if "id" in df.columns:
        print('"id" column present')
        # strip excess whitespace
        df["id"] = df["id"].apply(lambda X: X.strip())
    else:
        print('Cannot find "id" column')
        print("Columns present = {}".format(df.columns))
        return None
    # if we have fullname then we are good to go.
    if "studentName" in df.columns:
        print('"studentName" column present')
        df["studentName"].apply(lambda X: X.strip())
        return df

    # we need one of some approx of last-name field
    name0list = ["surname", "familyName", "lastName"]
    name0 = None
    for X in df.columns:
        if X.casefold() in (n.casefold() for n in name0list):
            print('"{}" column present'.format(X))
            name0 = X
            break
    if name0 is None:
        print('Cannot find column to use for "surname", tried {}'.format(name0list))
        print("Columns present = {}".format(df.columns))
        return None
    # strip the excess whitespace
    df[name0] = df[name0].apply(lambda X: X.strip())

    # we need one of some approx of given-name field
    name1list = [
        "name",
        "givenName",
        "firstName",
        "givenNames",
        "firstNames",
        "preferredName",
        "preferredNames",
        "nickName",
        "nickNames",
    ]
    name1 = None
    for X in df.columns:
        if X.casefold() in (n.casefold() for n in name1list):
            print('"{}" column present'.format(X))
            name1 = X
            break
    if name1 is None:
        print('Cannot find column to use for "given name", tried {}'.format(name1list))
        print("Columns present = {}".format(df.columns))
        return None
    # strip the excess whitespace
    df[name1] = df[name1].apply(lambda X: X.strip())

    # concat name0 and name1 fields into fullName field
    # strip excess whitespace from those fields
    df["studentName"] = df[name0] + ", " + df[name1]

    return df


def checkLatinNames(df):
    """Pass the pandas object and check studentNames encode to Latin-1.

    Print out a warning message for any that are not.
    """
    # TODO - make this less eurocentric in the future.
    problems = []
    for index, row in df.iterrows():
        try:
            tmp = row["studentName"].encode("Latin-1")
        except UnicodeEncodeError:
            problems.append(
                'row {}, number {}, name: "{}"'.format(
                    index, row["id"], row["studentName"]
                )
            )
    if len(problems) > 0:
        print("WARNING: The following ID/name pairs contain non-Latin characters:")
        for X in problems:
            print(X)
        return False
    else:
        return True


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
            # set server address, message port
            self.info = {"server": "127.0.0.1", "mport": 41984}

    def putInfoIntoUi(self):
        """Grab the values from the info dict and put into the UI fields
        """
        self.ui.serverLE.setText(self.info["server"])
        self.ui.mportSB.setValue(self.info["mport"])

    def saveAndClose(self):
        """Grab values from the UI, put into dictionary and save as json.
        Then close.
        """
        self.info["server"] = self.ui.serverLE.text()
        self.info["mport"] = self.ui.mportSB.value()

        fh = open("../resources/serverDetails.json", "w")
        fh.write(json.dumps(self.info, indent=4, sort_keys=True))
        fh.close()
        self.close()

    def manageUsers(self):
        """Fire up the user manager app."""
        subprocess.run(["python3", "./userManager.py"], check=True)

    def getClassList(self):
        """Grab list of student numbers and names from a csv file.

        Student numbers come from an `id` column.  There is some
        flexibility about student names: most straightforward is a
        column named `studentNames`.  Otherwise, various columns such as
        `surname` and `name` are tried.

        Alternatively, a csv file exported from Canvas can be provided.
        """
        # Pop up a message box with instructions
        QMessageBox.question(
            self,
            "Class list format",
            "Class list must be a CSV with column headers"
            '\n(*) "id" - student ID number'
            '\n(*) student name in a single field = "studentName"  *or*'
            "\n(*) student name split in two fields:"
            '\n--->["surname" or "familyName" or "lastName"] *and*'
            '\n--->["name" or "firstName" or "givenName" or "nickName" or "preferredName"].'
            "\n\nAlternatively, give csv exported from Canvas.",
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
            if all(
                x in fields for x in ("Student", "ID", "SIS User ID", "SIS Login ID")
            ):
                print("This looks like it was exported from Canvas")
                df = import_canvas_csv(fname)
                print("Extracting columns from Canvas data and renaming")
                df = df[["Student Number", "Student"]]
                df.columns = ["id", "studentName"]
            else:  # Is not canvas so check we have required headers
                df = checkNonCanvasCSV(fname)
                if df is None:
                    QMessageBox.question(
                        self,
                        "Classlist error",
                        "Problems with the classlist you supplied. See console output.",
                        buttons=QMessageBox.Ok,
                    )
                    return
                df = df[["id", "studentName"]]

            # check characters in names are latin-1 compatible
            if not checkLatinNames(df):
                QMessageBox.question(
                    self,
                    "Potential classlist problems",
                    "The classlist you supplied contains non-Latin characters - see console output. "
                    "You can proceed, but it might cause problems later. "
                    "Apologies for the eurocentricity.",
                    buttons=QMessageBox.Ok,
                )

            print("Saving to classlist.csv")
            df.to_csv("../resources/classlist.csv", index=False)
            return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SetUp()
    window.show()
    rv = app.exec_()
    sys.exit(rv)
