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
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QStyleFactory,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from uiFiles.ui_iic import Ui_IIC
from useful_classes import ErrorMessage, SimpleMessage
from plom_exceptions import *

import managerMessenger

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import __version__
from resources.version import Plom_API_Version


class ProgressBox(QGroupBox):
    def __init__(self, qu, v, stats):
        super(ProgressBox, self).__init__()
        self.question = qu
        self.version = v
        self.setTitle("Q-{} V-{}".format(qu, v))

        self.stats = stats
        grid = QVBoxLayout()
        self.avgL = QLabel()
        grid.addWidget(self.avgL)
        self.mtL = QLabel()
        grid.addWidget(self.mtL)
        self.lhL = QLabel()
        grid.addWidget(self.lhL)

        self.pb = QProgressBar()
        self.pb.setFormat("%v / %m")
        grid.addWidget(self.pb)

        self.setLayout(grid)
        self.show()
        self.refresh(self.stats)

    def refresh(self, stats):
        self.stats = stats
        if self.stats["NScanned"] == 0:
            self.setEnabled(False)
            return

        self.setEnabled(True)
        self.pb.setMaximum(self.stats["NScanned"])
        self.pb.setValue(self.stats["NMarked"])
        self.avgL.setText("Average mark = {}".format(self.stats["avgMark"]))
        self.mtL.setText("Marking time = {}".format(self.stats["avgMTime"]))
        self.lhL.setText("# in last hour = {}".format(self.stats["NRecent"]))


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
        self.connectButtons()

    def connectButtons(self):
        self.ui.loginButton.clicked.connect(self.login)
        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.fontButton.clicked.connect(self.setFont)
        self.ui.refreshIButton.clicked.connect(self.refreshIList)
        self.ui.refreshPButton.clicked.connect(self.refreshMTab)
        self.ui.refreshSButton.clicked.connect(self.refreshSList)

    def closeWindow(self):
        self.close()

    def setFont(self):
        v = self.ui.fontSB.value()
        fnt = self.parent.font()
        fnt.setPointSize(v)
        self.parent.setFont(fnt)

    def login(self):
        # Check username is a reasonable string
        user = self.ui.userLE.text()
        if (not user.isalnum()) or (not user):
            return
        # check password at least 4 char long
        pwd = self.ui.passwordLE.text()
        if len(pwd) < 4:
            return
        server = self.ui.serverLE.text()
        mport = self.ui.mportSB.value()

        # Have Messenger login into to server
        managerMessenger.setServerDetails(server, mport)
        managerMessenger.startMessenger()

        try:
            managerMessenger.requestAndSaveToken(user, pwd)
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
        except PlomSeriousException as e:
            ErrorMessage(
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e)
            ).exec_()
            return

        self.ui.scanTab.setEnabled(True)
        self.ui.progressTab.setEnabled(True)
        self.ui.userGBox.setEnabled(False)
        self.ui.serverGBox.setEnabled(False)
        self.ui.loginButton.setEnabled(False)

        self.getPQV()
        self.initScanTab()
        self.initMarkTab()

    # -------------------
    def getPQV(self):
        pqv = managerMessenger.getInfoPQV()
        self.numberOfPages = pqv[0]
        self.numberOfQuestions = pqv[1]
        self.numberOfVersions = pqv[2]

    def initScanTab(self):
        scanned = managerMessenger.getScannedTests()
        incomplete = managerMessenger.getIncompleteTests()
        self.ui.scanTW.setHeaderLabels(["Test number", "Page number"])
        self.ui.incompTW.setHeaderLabels(["Test number", "Missing page"])

        for t in incomplete:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for p in incomplete[t]:
                l0.addChild(QTreeWidgetItem(["", "{}".format(p)]))
            self.ui.incompTW.addTopLevelItem(l0)

        for t in scanned:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for p in range(self.numberOfPages):
                l0.addChild(QTreeWidgetItem(["", "{}".format(p + 1)]))
            self.ui.scanTW.addTopLevelItem(l0)

    def refreshIList(self):
        pass

    def refreshSList(self):
        pass

    def initMarkTab(self):
        grid = QGridLayout()
        self.pd = {}
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = managerMessenger.getProgress(q, v)
                self.pd[(q, v)] = ProgressBox(q, v, stats)
                grid.addWidget(self.pd[(q, v)], q, v)
        self.ui.markBucket.setLayout(grid)

    def refreshMTab(self):
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = managerMessenger.getProgress(q, v)
                self.pd[(q, v)].refresh(stats)


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
