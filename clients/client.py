#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import marker
import identifier
import totaler
import signal
import sys
import traceback as tblib
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialog, QStyleFactory, QMessageBox
from uiFiles.ui_chooser import Ui_Chooser
from useful_classes import ErrorMessage, SimpleMessage
import plom_exceptions

import messenger

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import __version__
from resources.version import Plom_API_Version

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


class Chooser(QDialog):
    def __init__(self, parent):
        self.APIVersion = Plom_API_Version
        super(Chooser, self).__init__()
        self.parent = parent
        print(
            "Plom Client {} (communicates with api {})".format(
                __version__, self.APIVersion
            )
        )
        # runit = either marker or identifier clients.
        self.runIt = None

        self.ui = Ui_Chooser()
        self.ui.setupUi(self)
        # Append version to window title
        self.setWindowTitle("{} {}".format(self.windowTitle(), __version__))
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
        # save those settings
        self.saveDetails()

        # Have Messenger login into to server
        messenger.setServerDetails(server, mport, wport)
        messenger.startMessenger()
        try:
            messenger.requestAndSaveToken(user, pwd)
        except plom_exceptions.PlomAPIException as e:
            ErrorMessage(
                "Could not authenticate due to API mismatch."
                "Your client version is {}.\n\n"
                "Error was: {}".format(__version__, e)
            ).exec_()
            return
        except plom_exceptions.BenignException as e:
            ErrorMessage("Could not authenticate: {}".format(e)).exec_()
            return
        except plom_exceptions.SeriousError as e:
            ErrorMessage(
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e)
            ).exec_()
            return

        # Now run the appropriate client sub-application
        if self.runIt == "Marker":
            # Run the marker client.
            pg = str(self.ui.pgSB.value()).zfill(2)
            v = str(self.ui.vSB.value())
            self.setEnabled(False)
            self.hide()
            markerwin = marker.MarkerClient(messenger, pg, v)
            markerwin.my_shutdown_signal.connect(self.on_other_window_close)
            markerwin.show()
            self.parent.marker = markerwin
        elif self.runIt == "IDer":
            # Run the ID client.
            self.setEnabled(False)
            self.hide()
            idwin = identifier.IDClient()
            idwin.my_shutdown_signal.connect(self.on_other_window_close)
            idwin.show()
            idwin.getToWork(messenger)
            self.parent.identifier = idwin
        else:
            # Run the Total client.
            self.setEnabled(False)
            self.hide()
            totalerwin = totaler.TotalClient()
            totalerwin.my_shutdown_signal.connect(self.on_other_window_close)
            totalerwin.show()
            totalerwin.getToWork(messenger)
            self.parent.totaler = totalerwin

    def runMarker(self):
        self.runIt = "Marker"
        self.validate()

    def runIDer(self):
        self.runIt = "IDer"
        self.validate()

    def runTotaler(self):
        self.runIt = "Totaler"
        self.validate()

    def saveDetails(self):
        lastTime["user"] = self.ui.userLE.text()
        lastTime["server"] = self.ui.serverLE.text()
        lastTime["mport"] = self.ui.mportSB.value()
        lastTime["wport"] = self.ui.wportSB.value()
        lastTime["pg"] = self.ui.pgSB.value()
        lastTime["v"] = self.ui.vSB.value()
        lastTime["fontSize"] = self.ui.fontSB.value()
        writeLastTime()

    def closeWindow(self):
        self.saveDetails()
        self.close()

    def setFont(self):
        v = self.ui.fontSB.value()
        fnt = self.parent.font()
        fnt.setPointSize(v)
        self.parent.setFont(fnt)

    @pyqtSlot(int)
    def on_other_window_close(self, value):
        assert isinstance(value, int)
        self.show()
        self.setEnabled(True)


# Pop up a dialog for unhandled exceptions and then exit
sys._excepthook = sys.excepthook


def _exception_hook(exctype, value, traceback):
    s = "".join(tblib.format_exception(exctype, value, traceback))
    mb = QMessageBox()
    mb.setText(
        "Something unexpected has happened!\n\n"
        "Please file a bug and copy-paste the following:\n\n"
        "{0}".format(s)
    )
    mb.setStandardButtons(QMessageBox.Ok)
    mb.exec_()
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


sys.excepthook = _exception_hook


class Plom(QApplication):
    def __init__(self, argv):
        super(Plom, self).__init__(argv)


# in order to have a graceful exit on control-c
# https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co?noredirect=1&lq=1
def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    sys.stderr.write("\r")
    if (
        QMessageBox.question(
            None,
            "",
            "Are you sure you want to force-quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        == QMessageBox.Yes
    ):
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    signal.signal(signal.SIGINT, sigint_handler)

    # create a small timer here, so that we can
    # kill the app with ctrl-c.
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(1000)
    # got this solution from
    # https://machinekoder.com/how-to-not-shoot-yourself-in-the-foot-using-python-qt/

    window = Chooser(app)
    window.show()
    sys.exit(app.exec_())
