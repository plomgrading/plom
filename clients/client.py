__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPLv3"

import json
import os
import marker
import identifier
import totaler
import sys
import traceback as tblib
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QStyleFactory, QMessageBox
from uiFiles.ui_chooser import Ui_Chooser

# set up variables to store paths for marker and id clients
global tempDirectory, directoryPath
# to store login + options for next run of client.
lastTime = {}


def readLastTime():
    """Read the login + server options that were used on
    the last run of the client.
    """
    global lastTime
    # set some reasonable defaults.
    lastTime["user"] = ""
    lastTime["server"] = "localhost"
    lastTime["mport"] = "41984"
    lastTime["wport"] = "41985"
    lastTime["pg"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    # If exists, read from json file.
    if os.path.isfile("lastTime.json"):
        with open("lastTime.json") as data_file:
            # update values from the json
            lastTime.update(json.load(data_file))


def writeLastTime():
    # Write the options to json file.
    fh = open("lastTime.json", "w")
    fh.write(json.dumps(lastTime, indent=4, sort_keys=True))
    fh.close()


class Chooser(QWidget):
    def __init__(self, parent):
        super(Chooser, self).__init__()
        self.parent = parent
        # runit = either marker or identifier clients.
        self.runIt = None
        # will be the marker-widget
        self.marker = None
        # will be the id-widget
        self.identifier = None

        self.ui = Ui_Chooser()
        self.ui.setupUi(self)
        # load in the login etc from last time (if exists)
        self.setLastTime()
        # connect buttons to functions.
        self.ui.markButton.clicked.connect(self.runMarker)
        self.ui.identifyButton.clicked.connect(self.runIDer)
        self.ui.totalButton.clicked.connect(self.runTotaler)
        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.fontButton.clicked.connect(self.setFont)

    def setLastTime(self):
        # set login etc from last time client ran.
        readLastTime()
        self.ui.userLE.setText(lastTime["user"])
        self.ui.serverLE.setText(lastTime["server"])
        self.ui.mportSB.setValue(int(lastTime["mport"]))
        self.ui.wportSB.setValue(int(lastTime["wport"]))
        self.ui.pgSB.setValue(int(lastTime["pg"]))
        self.ui.vSB.setValue(int(lastTime["v"]))
        self.ui.fontSB.setValue(int(lastTime["fontSize"]))
        self.setFont()

    def validate(self):
        # Check username is a reasonable string
        user = self.ui.userLE.text()
        if (not user.isalnum()) or (not user):
            return
        # check password at least 4 char long
        pwd = self.ui.passwordLE.text()
        if len(pwd) < 4:
            return
        # set server, message port, webdave port.
        server = self.ui.serverLE.text()
        mport = self.ui.mportSB.value()
        wport = self.ui.wportSB.value()
        # Now disable the server / user data entry
        self.ui.serverGBox.setEnabled(False)
        self.ui.userGBox.setEnabled(False)
        if self.runIt == "Marker":
            # Run the marker client.
            pg = str(self.ui.pgSB.value()).zfill(2)
            v = str(self.ui.vSB.value())
            self.marker = marker.MarkerClient(
                user, pwd, server, mport, wport, pg, v, self
            )
            self.marker.exec_()
        elif self.runIt == "IDer":
            # Run the ID client.
            self.identifier = identifier.IDClient(user, pwd, server, mport, wport)
            self.identifier.exec_()
        else:
            # Run the Total client.
            self.totaler = totaler.TotalClient(user, pwd, server, mport, wport)
            self.totaler.exec_()

    def runMarker(self):
        self.runIt = "Marker"
        self.validate()

    def runIDer(self):
        self.runIt = "IDer"
        self.validate()

    def runTotaler(self):
        self.runIt = "Totaler"
        self.validate()

    def closeWindow(self):
        lastTime["user"] = self.ui.userLE.text()
        lastTime["server"] = self.ui.serverLE.text()
        lastTime["mport"] = self.ui.mportSB.value()
        lastTime["wport"] = self.ui.wportSB.value()
        lastTime["pg"] = self.ui.pgSB.value()
        lastTime["v"] = self.ui.vSB.value()
        lastTime["fontSize"] = self.ui.fontSB.value()

        writeLastTime()

        self.close()

    def setFont(self):
        v = self.ui.fontSB.value()
        fnt = self.parent.font()
        fnt.setPointSize(v)
        self.parent.setFont(fnt)


# Pop up a dialog for unhandled exceptions and then exit
sys._excepthook = sys.excepthook
def _exception_hook(exctype, value, traceback):
    s = "".join(tblib.format_exception(exctype, value, traceback))
    mb = QMessageBox()
    mb.setText("Something unexpected has happened!\n\n"
               "Please file a bug and copy-paste the following:\n\n"
               "{0}".format(s))
    mb.setStandardButtons(QMessageBox.Ok)
    mb.exec_()
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = _exception_hook


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create("Fusion"))

window = Chooser(app)
window.show()
rv = app.exec_()
sys.exit(rv)
