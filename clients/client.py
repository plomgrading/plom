#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import toml
import argparse
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
from plom_exceptions import *

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
    lastTime["pg"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["upDown"] = "up"
    lastTime["mouse"] = "right"
    # If config file exists, use it to update the defaults
    if os.path.isfile("plomConfig.toml"):
        with open("plomConfig.toml") as data_file:
            lastTime.update(toml.load(data_file))


def writeLastTime():
    """Write the options to the config file."""
    fh = open("plomConfig.toml", "w")
    fh.write(toml.dumps(lastTime))
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
        self.ui.getServerInfoButton.clicked.connect(self.getInfo)
        self.ui.serverLE.textEdited.connect(self.ungetInfo)
        self.ui.mportSB.valueChanged.connect(self.ungetInfo)
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.setVisible(False)

    def setLastTime(self):
        # set login etc from last time client ran.
        readLastTime()
        self.ui.userLE.setText(lastTime["user"])
        self.ui.serverLE.setText(lastTime["server"])
        self.ui.mportSB.setValue(int(lastTime["mport"]))
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
        server = self.ui.serverLE.text()
        if not server:
            return
        mport = self.ui.mportSB.value()
        # save those settings
        self.saveDetails()

        # Have Messenger login into to server
        messenger.setServerDetails(server, mport)
        try:
            messenger.startMessenger()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n" "{}".format(e)).exec_()
            return

        try:
            messenger.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            ErrorMessage(
                "Could not authenticate due to API mismatch."
                "Your client version is {}.\n\n"
                "Error was: {}".format(__version__, e)
            ).exec_()
            return
        except PlomAuthenticationException as e:
            ErrorMessage("Could not authenticate: {}".format(e)).exec_()
            return
        except PlomExistingLoginException as e:
            ErrorMessage("You appear to be logged in already").exec_()
            if (
                SimpleMessage(
                    "Should I force-logout the existing authorisation?"
                ).exec_()
                == QMessageBox.Yes
            ):
                messenger.clearAuthorisation(user, pwd)
            return

        except PlomSeriousException as e:
            ErrorMessage(
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e)
            ).exec_()
            return

        # Now run the appropriate client sub-application
        if self.runIt == "Marker":
            # Run the marker client.
            pg = self.getpg()
            v = self.getv()
            self.setEnabled(False)
            self.hide()
            markerwin = marker.MarkerClient()
            markerwin.my_shutdown_signal.connect(self.on_marker_window_close)
            markerwin.show()
            markerwin.getToWork(messenger, pg, v, lastTime)
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
        lastTime["pg"] = self.getpg()
        lastTime["v"] = self.getv()
        lastTime["fontSize"] = self.ui.fontSB.value()
        writeLastTime()

    def closeWindow(self):
        self.saveDetails()
        messenger.stopMessenger()
        self.close()

    def setFont(self):
        v = self.ui.fontSB.value()
        fnt = self.parent.font()
        fnt.setPointSize(v)
        self.parent.setFont(fnt)

    def getpg(self):
        """Return the integer pagegroup or None"""
        if self.ui.pgDrop.isVisible():
            pg = self.ui.pgDrop.currentText().lstrip("Q")
        else:
            pg = self.ui.pgSB.value()
        try:
            return int(pg)
        except:
            return None

    def getv(self):
        """Return the integer version or None"""
        if self.ui.vDrop.isVisible():
            v = self.ui.vDrop.currentText()
        else:
            v = self.ui.vSB.value()
        try:
            return int(v)
        except:
            return None

    def ungetInfo(self):
        self.ui.markGBox.setTitle("Marking information")
        pg = self.getpg()
        v = self.getv()
        self.ui.pgSB.setVisible(True)
        self.ui.vSB.setVisible(True)
        if pg:
            self.ui.pgSB.setValue(pg)
        if v:
            self.ui.vSB.setValue(v)
        self.ui.vDrop.clear()
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.clear()
        self.ui.pgDrop.setVisible(False)
        self.ui.infoLabel.setText("")
        messenger.stopMessenger()

    def getInfo(self):
        server = self.ui.serverLE.text()
        if not server:
            return
        mport = self.ui.mportSB.value()
        # save those settings
        # self.saveDetails()   # TODO?

        # TODO: might be nice, but needs another thread?
        # self.ui.infoLabel.setText("connecting...")
        # self.ui.infoLabel.repaint()

        # Have Messenger login into to server
        messenger.setServerDetails(server, mport)
        try:
            r = messenger.startMessenger()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n" "{}".format(e)).exec_()
            return
        self.ui.infoLabel.setText(r)

        info = messenger.getInfoGeneral()
        self.ui.markGBox.setTitle(
            "Marking information for “{}”".format(info["testName"])
        )
        pg = self.getpg()
        v = self.getv()
        self.ui.pgSB.setVisible(False)
        self.ui.vSB.setVisible(False)

        self.ui.vDrop.clear()
        self.ui.vDrop.addItems([str(x + 1) for x in range(0, info["numVersions"])])
        if v:
            if v >= 1 and v <= info["numVersions"]:
                self.ui.vDrop.setCurrentIndex(v - 1)
        self.ui.vDrop.setVisible(True)

        self.ui.pgDrop.clear()
        self.ui.pgDrop.addItems(
            ["Q{}".format(x + 1) for x in range(0, info["numGroups"])]
        )
        if pg:
            if pg >= 1 and pg <= info["numGroups"]:
                self.ui.pgDrop.setCurrentIndex(pg - 1)
        self.ui.pgDrop.setVisible(True)
        # TODO should we also let people type in?
        self.ui.pgDrop.setEditable(False)
        self.ui.vDrop.setEditable(False)
        # put focus at password line-edit
        self.ui.passwordLE.setFocus(True)

    @pyqtSlot(int)
    def on_other_window_close(self, value):
        assert isinstance(value, int)
        self.show()
        self.setEnabled(True)

    @pyqtSlot(int, list)
    def on_marker_window_close(self, value, stuff):
        assert isinstance(value, int)
        self.show()
        self.setEnabled(True)
        if not stuff:
            return
        # update mouse-hand and up/down style for lasttime file
        markStyle, mouseHand = stuff
        global lastTime
        if markStyle == 2:
            lastTime["upDown"] = "up"
        elif markStyle == 3:
            lastTime["upDown"] = "down"
        else:
            raise RuntimeError("tertium non datur")
        if mouseHand == 0:
            lastTime["mouse"] = "right"
        elif mouseHand == 1:
            lastTime["mouse"] = "left"
        else:
            raise RuntimeError("tertium non datur")


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

    # Command line arguments (currently undocumented/unsupported)
    # either nothing, or the following
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description="Run the Plom client. No arguments = run as normal."
        )
        parser.add_argument("user", type=str)
        parser.add_argument("password", type=str)
        parser.add_argument(
            "-s", "--server", action="store", help="Which server to contact."
        )
        parser.add_argument("-p", "--port", action="store", help="Which port to use.")

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "-i", "--identifier", action="store_true", help="Run the identifier"
        )
        group.add_argument(
            "-t", "--totaler", action="store_true", help="Run the totaler"
        )
        group.add_argument(
            "-m",
            "--marker",
            const="json",
            nargs="?",
            type=str,
            help="Run the marker. Pass either -m n:k (to run on pagegroup n, version k) or -m (to run on whatever was used last time).",
        )
        args = parser.parse_args()

        window.ui.userLE.setText(args.user)
        window.ui.passwordLE.setText(args.password)
        if args.server:
            window.ui.serverLE.setText(args.server)
        if args.port:
            window.ui.mportSB.setValue(int(args.port))

        if args.identifier:
            window.ui.identifyButton.animateClick()
        if args.totaler:
            window.ui.totalButton.animateClick()
        if args.marker:
            if args.marker != "json":
                pg, v = args.marker.split(":")
                try:
                    window.ui.pgSB.setValue(int(pg))
                    window.ui.vSB.setValue(int(v))
                except ValueError:
                    print(
                        "When you use -m, there should either be no argument, or an argument of the form n:k where n,k are integers."
                    )
                    quit()

            window.ui.markButton.animateClick()
    sys.exit(app.exec_())
