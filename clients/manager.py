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
from PyQt5.QtGui import QFont, QStandardItem, QStandardItemModel
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
        self.nscL = QLabel()
        grid.addWidget(self.nscL)
        self.nmkL = QLabel()
        grid.addWidget(self.nmkL)
        self.lhL = QLabel()
        grid.addWidget(self.lhL)
        self.mtL = QLabel()
        grid.addWidget(self.mtL)
        self.avgL = QLabel()
        grid.addWidget(self.avgL)

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
        self.nscL.setText("# Scanned = {}".format(self.stats["NScanned"]))
        self.nmkL.setText("# Marked = {}".format(self.stats["NMarked"]))
        self.avgL.setText("Average mark = {}".format(self.stats["avgMark"]))
        self.mtL.setText("Marking time = {}".format(self.stats["avgMTime"]))
        self.lhL.setText("# Marked in last hour = {}".format(self.stats["NRecent"]))


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
        self.ui.removePageB.clicked.connect(self.removePage)
        self.ui.subsPageB.clicked.connect(self.subsPage)

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
        self.initUnknownTab()

    # -------------------
    def getPQV(self):
        pqv = managerMessenger.getInfoPQV()
        self.numberOfPages = pqv[0]
        self.numberOfQuestions = pqv[1]
        self.numberOfVersions = pqv[2]

    def initScanTab(self):
        self.ui.scanTW.setHeaderLabels(["Test number", "Page number", "Version"])
        self.ui.incompTW.setHeaderLabels(["Test number", "Missing page", "Version"])
        self.refreshIList()

        scanned = managerMessenger.getScannedTests()
        for t in scanned:
            l0 = QTreeWidgetItem(["{}".format(t)])
            for (p, v) in scanned[t]:
                l0.addChild(QTreeWidgetItem(["", str(p), str(v)]))
            self.ui.scanTW.addTopLevelItem(l0)

    def refreshIList(self):
        # delete the children of each toplevel items
        root = self.ui.incompTW.invisibleRootItem()
        for l0 in range(self.ui.incompTW.topLevelItemCount()):
            l0i = self.ui.incompTW.topLevelItem(0)
            for l1 in range(self.ui.incompTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        incomplete = managerMessenger.getIncompleteTests()  # pairs [p,v]
        for t in incomplete:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for (p, v) in incomplete[t]:
                l0.addChild(QTreeWidgetItem(["", str(p), str(v)]))
            self.ui.incompTW.addTopLevelItem(l0)

    def refreshSList(self):
        # delete the children of each toplevel items
        root = self.ui.scanTW.invisibleRootItem()
        for l0 in range(self.ui.scanTW.topLevelItemCount()):
            l0i = self.ui.scanTW.topLevelItem(0)
            for l1 in range(self.ui.scanTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        scanned = managerMessenger.getScannedTests()  # pairs [p,v]
        for t in scanned:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for (p, v) in scanned[t]:
                l0.addChild(QTreeWidgetItem(["", str(p), str(v)]))
            self.ui.scanTW.addTopLevelItem(l0)

    def removePage(self):
        # THIS SHOULD KEEP VERSION INFORMATION
        pvi = self.ui.scanTW.selectedItems()
        # if nothing selected - return
        if len(pvi) == 0:
            return
        # if selected a top-level item (ie a test) - return
        if pvi[0].childCount() > 0:
            return
        pp = int(pvi[0].text(1))
        pv = int(pvi[0].text(2))
        pt = int(pvi[0].parent().text(0))  # grab test number from parent
        msg = SimpleMessage(
            "Are you sure you want to remove (p/v) = ({}/{}) of test {}?".format(
                pp, pv, pt
            )
        )
        if msg.exec_() == QMessageBox.No:
            return
        else:
            code = "t{}p{}v{}".format(str(pt).zfill(4), str(pp).zfill(2), pv)
            rval = managerMessenger.removeScannedPage(code, pt, pp, pv)
            ErrorMessage("{}".format(rval)).exec_()
            self.refreshSList()

    def subsPage(self):
        # THIS SHOULD KEEP VERSION INFORMATION
        pvi = self.ui.incompTW.selectedItems()
        # if nothing selected - return
        if len(pvi) == 0:
            return
        # if selected a top-level item (ie a test) - return
        if pvi[0].childCount() > 0:
            return
        pp = int(pvi[0].text(1))
        pv = int(pvi[0].text(2))
        pt = int(pvi[0].parent().text(0))  # grab test number from parent
        msg = SimpleMessage(
            'Are you sure you want to substitute a "Missing Page" blank for (p/v) = ({}/{}) of test {}?'.format(
                pp, pv, pt
            )
        )
        if msg.exec_() == QMessageBox.No:
            return
        else:
            code = "t{}p{}v{}".format(str(pt).zfill(4), str(pp).zfill(2), pv)
            rval = managerMessenger.replaceMissingPage(code, pt, pp, pv)
            ErrorMessage("{}".format(rval)).exec_()
            self.refeshIList()

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

    def todo(self, msg=""):
        ErrorMessage("This is on our to-do list" + msg).exec_()

    def initUnknownTab(self):
        self.unknownModel = QStandardItemModel(self.ui.unknownLV)
        self.ui.unknownLV.setModel(self.unknownModel)
        self.refreshUList()

    def refreshUList(self):
        unkList = managerMessenger.getUnknownPageNames()
        for u in unkList:
            self.unknownModel.appendRow(QStandardItem(u))


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
