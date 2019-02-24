__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai", "Matt Coles"]
__license__ = "GPLv3"

import json
import os
import marker
import identifier
import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QWidget, QStyleFactory
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
    # If exists, read from json file.
    if os.path.isfile("lastTime.json"):
        with open("lastTime.json") as data_file:
            lastTime = json.load(data_file)
    else:
        # set some reasonable defaults.
        lastTime["user"] = ""
        lastTime["server"] = "localhost"
        lastTime["mport"] = "41984"
        lastTime["wport"] = "41985"
        lastTime["pg"] = 1
        lastTime["v"] = 1
        lastTime["fontSize"] = 10


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
        else:
            # Run the ID client.
            self.identifier = identifier.IDClient(user, pwd, server, mport, wport)
            self.identifier.exec_()

    def runMarker(self):
        self.runIt = "Marker"
        self.validate()

    def runIDer(self):
        self.runIt = "IDer"
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


app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create("Fusion"))
## To try to sort out font size scaling we poll the DPI
# fntscale = 96.0 / QWidget().logicalDpiY()  # UI was built on system with dpiy=96
# print("Local dpiy = {}".format(QWidget().logicalDpiY()))
# print("UI was built with dpiy = 96, so scaling by {}".format(fntscale))
# fnt = app.font()
# fntsize = fnt.pointSizeF() * fntscale  # scale the font size.
# fnt.setPointSizeF(fntsize)
# app.setFont(fnt)

window = Chooser(app)
window.show()
rv = app.exec_()
sys.exit(rv)
