#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
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
from PyQt5.QtWidgets import QApplication, QDialog, QStyleFactory, QMessageBox, QWidget
from uiFiles.ui_iic import Ui_IIC
from useful_classes import ErrorMessage, SimpleMessage
from plom_exceptions import *


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


class Manager(QWidget):
    def __init__(self, parent):
        self.APIVersion = Plom_API_Version
        super(Manager, self).__init__()
        self.parent = parent
        print(
            "Plom Client {} (communicates with api {})".format(
                __version__, self.APIVersion
            )
        )
        self.ui = Ui_IIC()
        self.ui.setupUi(self)


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

    window = Manager(app)
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

        args = parser.parse_args()

        window.ui.userLE.setText(args.user)
        window.ui.passwordLE.setText(args.password)
        if args.server:
            window.ui.serverLE.setText(args.server)
        if args.port:
            window.ui.mportSB.setValue(int(args.port))
            window.ui.wportSB.setValue(int(args.port) + 1)

    sys.exit(app.exec_())
