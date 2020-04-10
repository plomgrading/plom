#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import toml
import argparse
import os
import csv
import signal
import sys
import tempfile
import traceback as tblib
from PyQt5.QtCore import Qt, pyqtSlot, QRectF, QSize, QTimer
from PyQt5.QtGui import QBrush, QFont, QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QGroupBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyleFactory,
    QTableWidgetItem,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# TODO: client references to be avoided, refactor to common utils?
from plom.client.useful_classes import ErrorMessage, SimpleMessage
from plom.client.origscanviewer import WholeTestView, GroupView

from .uiFiles.ui_manager import Ui_Manager
from .unknownpageview import UnknownViewWindow
from .collideview import CollideViewWindow
from .discardview import DiscardViewWindow
from .reviewview import ReviewViewWindow
from .selectrectangle import SelectRectangleWindow, IDViewWindow
from plom.plom_exceptions import *
from plom.messenger import ManagerMessenger

from plom import __version__, Plom_API_Version, Default_Port


class QVHistogram(QDialog):
    def __init__(self, q, v, hist):
        super(QVHistogram, self).__init__()
        self.question = q
        self.version = v
        self.setWindowTitle("Histograms")
        self.hist = hist
        tot = 0
        mx = 0
        dist = {}
        for u in self.hist:
            for m in self.hist[u]:
                im = int(m)
                s = int(self.hist[u][m])
                mx = max(mx, im)
                tot += s
                if im not in dist:
                    dist[im] = 0
                dist[im] += s

        grid = QVBoxLayout()
        grid.addWidget(QLabel("Histograms for question {} version {}".format(q, v)))

        self.eG = QGroupBox("All markers")
        gg = QVBoxLayout()
        gg.addWidget(QLabel("Number of papers: {}".format(tot)))
        gp = QHBoxLayout()
        for im in range(0, mx + 1):
            pb = QProgressBar()
            pb.setOrientation(Qt.Vertical)
            if im not in dist:
                pb.setValue(0)
            else:
                pb.setValue((100 * dist[im]) // tot)
            pb.setToolTip("{} = {}%".format(im, pb.value()))
            gp.addWidget(pb)
        gg.addLayout(gp)
        self.eG.setLayout(gg)
        grid.addWidget(self.eG)

        self.uG = {}
        for u in self.hist:
            utot = 0
            for m in self.hist[u]:
                utot += self.hist[u][m]
            self.uG[u] = QGroupBox("Marker: {}".format(u))
            gg = QVBoxLayout()
            gg.addWidget(QLabel("Number of papers: {}".format(utot)))
            gp = QHBoxLayout()
            for im in range(0, mx + 1):
                m = str(im)
                pb = QProgressBar()
                pb.setOrientation(Qt.Vertical)
                if m not in self.hist[u]:
                    pb.setValue(0)
                else:
                    pb.setValue((100 * self.hist[u][m]) // utot)
                pb.setToolTip("{} = {}%".format(m, pb.value()))
                gp.addWidget(pb)
            gg.addLayout(gp)
            self.uG[u].setLayout(gg)
            grid.addWidget(self.uG[u])

        self.cB = QPushButton("&Close")
        self.cB.clicked.connect(self.accept)
        grid.addWidget(self.cB)
        self.setLayout(grid)
        self.show()


class TestStatus(QDialog):
    def __init__(self, nq, status):
        super(TestStatus, self).__init__()
        self.status = status
        self.setWindowTitle("Status of test {}".format(self.status["number"]))

        grid = QGridLayout()
        self.idCB = QCheckBox("Identified: ")
        self.idCB.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.idCB.setFocusPolicy(Qt.NoFocus)
        if status["identified"]:
            self.idCB.setCheckState(Qt.Checked)
        self.totCB = QCheckBox("Totalled: ")
        self.totCB.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.totCB.setFocusPolicy(Qt.NoFocus)
        if status["totalled"]:
            self.totCB.setCheckState(Qt.Checked)
        self.mkCB = QCheckBox("Marked: ")
        self.mkCB.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.mkCB.setFocusPolicy(Qt.NoFocus)
        if status["marked"]:
            self.mkCB.setCheckState(Qt.Checked)

        self.clB = QPushButton("&close")
        self.clB.clicked.connect(self.accept)

        grid.addWidget(self.idCB, 1, 1)
        grid.addWidget(self.totCB, 1, 2)
        grid.addWidget(self.mkCB, 1, 3)

        if status["identified"]:
            self.iG = QGroupBox("Identification")
            gg = QVBoxLayout()
            gg.addWidget(QLabel("ID: {}".format(status["sid"])))
            gg.addWidget(QLabel("Name: {}".format(status["sname"])))
            gg.addWidget(QLabel("Username: {}".format(status["iwho"])))
            self.iG.setLayout(gg)
            grid.addWidget(self.iG, 2, 1, 3, 3)

        if status["totalled"]:
            self.tG = QGroupBox("Totalling")
            gg = QVBoxLayout()
            gg.addWidget(QLabel("Total: {}".format(status["total"])))
            gg.addWidget(QLabel("Username: {}".format(status["twho"])))
            self.tG.setLayout(gg)
            grid.addWidget(self.tG, 5, 1, 3, 3)

        self.qG = {}
        for q in range(1, nq + 1):
            sq = str(q)
            self.qG[q] = QGroupBox("Question {}.{}:".format(q, status[sq]["version"]))
            gg = QVBoxLayout()
            if status[sq]["marked"]:
                gg.addWidget(QLabel("Marked"))
                gg.addWidget(QLabel("Mark: {}".format(status[sq]["mark"])))
                gg.addWidget(QLabel("Username: {}".format(status[sq]["who"])))
            else:
                gg.addWidget(QLabel("Unmarked"))

            self.qG[q].setLayout(gg)
            grid.addWidget(self.qG[q], 10 * q + 1, 1, 3, 3)

        grid.addWidget(self.clB, 100, 10)
        self.setLayout(grid)


class ProgressBox(QGroupBox):
    def __init__(self, parent, qu, v, stats):
        super(ProgressBox, self).__init__()
        self.parent = parent
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
        self.vhB = QPushButton("View histograms")
        self.vhB.clicked.connect(self.viewHist)
        grid.addWidget(self.vhB)

        self.setLayout(grid)
        self.show()
        self.refresh(self.stats)

    def refresh(self, stats):
        self.stats = stats

        self.setEnabled(True)
        self.pb.setMaximum(self.stats["NScanned"])
        self.pb.setValue(self.stats["NMarked"])
        self.nscL.setText("# Scanned = {}".format(self.stats["NScanned"]))
        self.nmkL.setText("# Marked = {}".format(self.stats["NMarked"]))

        if self.stats["NScanned"] == 0:
            self.setEnabled(False)
            return
        if self.stats["NMarked"] > 0:
            self.avgL.setText("Average mark = {:0.2f}".format(self.stats["avgMark"]))
            self.mtL.setText("Marking time = {:0.2f}".format(self.stats["avgMTime"]))
            self.lhL.setText("# Marked in last hour = {}".format(self.stats["NRecent"]))
        else:
            self.avgL.setText("Average mark = N/A")
            self.mtL.setText("Marking time = N/A")
            self.lhL.setText("# Marked in last hour = N/A")

    def viewHist(self):
        self.parent.viewMarkHistogram(self.question, self.version)


class Manager(QWidget):
    def __init__(self, parent):
        self.APIVersion = Plom_API_Version
        super(Manager, self).__init__()
        self.parent = parent
        global managerMessenger
        managerMessenger = None
        print(
            "Plom Manager Client {} (communicates with api {})".format(
                __version__, self.APIVersion
            )
        )
        self.ui = Ui_Manager()
        self.ui.setupUi(self)
        self.ui.passwordLE.setFocus(True)
        self.connectButtons()
        self.ui.scanningAllTab.setEnabled(False)
        self.ui.progressAllTab.setEnabled(False)
        self.ui.reviewAllTab.setEnabled(False)
        self.ui.userAllTab.setEnabled(False)

    def connectButtons(self):
        self.ui.loginButton.clicked.connect(self.login)
        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.fontButton.clicked.connect(self.setFont)
        self.ui.refreshOButton.clicked.connect(self.refreshOTab)
        self.ui.refreshIDButon.clicked.connect(self.refreshIDTab)
        self.ui.refreshIButton.clicked.connect(self.refreshIList)
        self.ui.refreshPButton.clicked.connect(self.refreshMTab)
        self.ui.refreshTOB.clicked.connect(self.refreshOutTab)
        self.ui.refreshSButton.clicked.connect(self.refreshSList)
        self.ui.refreshUButton.clicked.connect(self.refreshUList)
        self.ui.refreshCButton.clicked.connect(self.refreshCList)
        self.ui.refreshDButton.clicked.connect(self.refreshDList)
        self.ui.refreshIDRevB.clicked.connect(self.refreshIDRev)
        self.ui.refreshTOTB.clicked.connect(self.refreshTOTRev)
        self.ui.refreshUserB.clicked.connect(self.refreshUserList)
        self.ui.refreshQPUB.clicked.connect(self.refreshQPU)
        self.ui.refreshPUQB.clicked.connect(self.refreshPUQ)

        self.ui.removePageB.clicked.connect(self.removePage)
        self.ui.subsPageB.clicked.connect(self.subsPage)
        self.ui.actionUButton.clicked.connect(self.doUActions)
        self.ui.actionCButton.clicked.connect(self.doCActions)
        self.ui.actionDButton.clicked.connect(self.doDActions)
        self.ui.selectRectButton.clicked.connect(self.selectRectangle)
        self.ui.predictButton.clicked.connect(self.runPredictor)
        self.ui.delPredButton.clicked.connect(self.deletePredictions)
        self.ui.predListRefreshB.clicked.connect(self.getPredictions)
        self.ui.forceLogoutB.clicked.connect(self.forceLogout)

    def closeWindow(self):
        global managerMessenger
        if managerMessenger is not None:
            managerMessenger.closeUser()
        self.close()

    def setServer(self, s):
        """Set the server and port UI widgets from a string.

        If port is missing, a default will be used."""
        try:
            s, p = s.split(":")
        except ValueError:
            p = Default_Port
        self.ui.serverLE.setText(s)
        self.ui.mportSB.setValue(int(p))

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
        global managerMessenger
        managerMessenger = ManagerMessenger(server, mport)
        managerMessenger.start()

        try:
            managerMessenger.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            ErrorMessage(
                "Could not authenticate due to API mismatch."
                "Your client version is {}.\n\n"
                "Error was: {}".format(__version__, e)
            ).exec_()
            return
        except PlomExistingLoginException as e:
            if (
                SimpleMessage(
                    "You appear to be already logged in!\n\n"
                    "  * Perhaps a previous session crashed?\n"
                    "  * Do you have another client running,\n"
                    "    e.g., on another computer?\n\n"
                    "Should I force-logout the existing authorisation?"
                    " (and then you can try to log in again)\n\n"
                    "The other client will likely crash."
                ).exec_()
                == QMessageBox.Yes
            ):
                managerMessenger.clearAuthorisation("manager", pwd)
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

        self.ui.scanningAllTab.setEnabled(True)
        self.ui.progressAllTab.setEnabled(True)
        self.ui.reviewAllTab.setEnabled(True)
        self.ui.userAllTab.setEnabled(True)

        self.ui.userGBox.setEnabled(False)
        self.ui.serverGBox.setEnabled(False)
        self.ui.loginButton.setEnabled(False)

        self.getTPQV()
        self.initOTab()
        self.initScanTab()
        self.initIDTab()
        self.initMarkTab()
        self.initOutTab()
        self.initUnknownTab()
        self.initCollideTab()
        self.initDiscardTab()
        self.initRevTab()
        self.initRevIDTab()
        self.initRevTOTTab()
        self.initUserListTab()
        self.initQPUTab()
        self.initPUQTab()

    # -------------------
    def getTPQV(self):
        info = managerMessenger.getInfoGeneral()
        self.numberOfTests = info["numberOfTests"]
        self.numberOfPages = info["numberOfPages"]
        self.numberOfQuestions = info["numberOfQuestions"]
        self.numberOfVersions = info["numberOfVersions"]

    def initOTab(self):
        self.ui.overallTW.setHorizontalHeaderLabels(
            ["Test number", "Identified", "Totalled", "Questions Marked"]
        )
        self.ui.overallTW.activated.connect(self.viewTestStatus)
        self.ui.overallTW.setSortingEnabled(True)
        self.refreshOTab()

    def viewTestStatus(self):
        pvi = self.ui.overallTW.selectedItems()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        testNumber = int(self.ui.overallTW.item(r, 0).text())
        stats = managerMessenger.RgetStatus(testNumber)
        TestStatus(self.numberOfQuestions, stats).exec_()

    def refreshOTab(self):
        self.ui.overallTW.clearContents()
        self.ui.overallTW.setRowCount(0)

        opDict = managerMessenger.RgetCompletions()
        tk = list(opDict.keys())
        tk.sort(key=int)  # sort in numeric order
        r = 0
        for t in tk:
            self.ui.overallTW.insertRow(r)
            self.ui.overallTW.setItem(r, 0, QTableWidgetItem(str(t).rjust(4)))
            it = QTableWidgetItem("{}".format(opDict[t][0]))
            if opDict[t][0]:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been identified")
            self.ui.overallTW.setItem(r, 1, it)

            it = QTableWidgetItem("{}".format(opDict[t][1]))
            if opDict[t][1]:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been totalled")
            self.ui.overallTW.setItem(r, 2, it)

            it = QTableWidgetItem(str(opDict[t][2]).rjust(2))
            if opDict[t][2] == self.numberOfQuestions:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been marked")
            self.ui.overallTW.setItem(r, 3, it)
            r += 1

    def initScanTab(self):
        self.ui.scanTW.setHeaderLabels(["Test number", "Page number", "Version"])
        self.ui.scanTW.activated.connect(self.viewSPage)
        self.ui.incompTW.setHeaderLabels(["Test number", "Page", "Version", "Status"])
        self.ui.incompTW.activated.connect(self.viewISTest)
        self.refreshIList()
        self.refreshSList()

    def refreshIList(self):
        # delete the children of each toplevel items
        root = self.ui.incompTW.invisibleRootItem()
        for l0 in range(self.ui.incompTW.topLevelItemCount()):
            l0i = self.ui.incompTW.topLevelItem(0)
            for l1 in range(self.ui.incompTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        incomplete = managerMessenger.getIncompleteTests()  # triples [p,v,true/false]
        for t in incomplete:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for (p, v, s) in incomplete[t]:
                if s:
                    l0.addChild(QTreeWidgetItem(["", str(p), str(v), "scanned"]))
                else:
                    it = QTreeWidgetItem(["", str(p), str(v), "missing"])
                    it.setBackground(3, QBrush(Qt.red))
                    l0.addChild(it)
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
        colDict = managerMessenger.getCollidingPageNames()  # dict [fname]=[t,p,v]
        cdtp = {u: "{}.{}".format(colDict[u][0], colDict[u][1]) for u in colDict}

        for t in scanned:
            l0 = QTreeWidgetItem(["{}".format(t), ""])
            for (p, v) in scanned[t]:
                l1 = QTreeWidgetItem(["", str(p), str(v)])
                if "{}.{}".format(t, p) in cdtp.values():
                    l0.setBackground(0, QBrush(Qt.cyan))
                    l0.setToolTip(0, "Has collisions")
                    l1.setBackground(1, QBrush(Qt.cyan))
                    l0.setToolTip(1, "Has collisions")
                l0.addChild(l1)
            self.ui.scanTW.addTopLevelItem(l0)

    def viewPage(self, t, p, v):
        vp = managerMessenger.getPageImage(t, p, v)
        if vp is None:
            return
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(vp)
            GroupView([fh.name]).exec_()

    def viewSPage(self):
        pvi = self.ui.scanTW.selectedItems()
        if len(pvi) == 0:
            return
        # if selected a top-level item (ie a test) - view the whole test
        if pvi[0].childCount() > 0:
            pt = int(pvi[0].text(0))
            self.viewWholeTest(pt)
            return
        pp = int(pvi[0].text(1))
        pv = int(pvi[0].text(2))
        pt = int(pvi[0].parent().text(0))  # grab test number from parent
        self.viewPage(pt, pp, pv)

    def viewISTest(self):
        pvi = self.ui.incompTW.selectedItems()
        if len(pvi) == 0:
            return
        # if selected a lower-level item (ie a missing page) - check if scanned
        if pvi[0].childCount() == 0:
            if pvi[0].text(3) == "scanned":
                self.viewPage(
                    int(pvi[0].parent().text(0)),
                    int(pvi[0].text(1)),
                    int(pvi[0].text(2)),
                )
            return
        # else fire up the whole test.
        self.viewWholeTest(int(pvi[0].text(0)))

    def removePage(self):
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
            self.refreshIList()

    def initIDTab(self):
        self.refreshIDTab()
        self.ui.idPB.setFormat("%v / %m")
        self.ui.totPB.setFormat("%v / %m")
        self.ui.predictionTW.setColumnCount(3)
        self.ui.predictionTW.setHorizontalHeaderLabels(["Test", "Student ID", "Name"])
        self.ui.predictionTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.predictionTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.predictionTW.setAlternatingRowColors(True)
        self.ui.predictionTW.activated.connect(self.viewIDPage)

    def refreshIDTab(self):
        ti = managerMessenger.IDprogressCount()
        tt = managerMessenger.TprogressCount()
        self.ui.papersLE.setText(str(ti[1]))
        self.ui.idPB.setValue(ti[0])
        self.ui.idPB.setMaximum(ti[1])
        self.ui.totPB.setMaximum(tt[1])
        self.ui.totPB.setValue(tt[0])
        self.getPredictions()

    def selectRectangle(self):
        imageList = managerMessenger.IDgetRandomImage()
        # Image names = "i<testnumber>.<imagenumber>.png"
        inames = []
        with tempfile.TemporaryDirectory() as td:
            for i in range(len(imageList)):
                tmp = os.path.join(td, "id.{}.png".format(i))
                inames.append(tmp)
                with open(tmp, "wb+") as fh:
                    fh.write(imageList[i])
            srw = SelectRectangleWindow(self, inames)
            if srw.exec_() == QDialog.Accepted:
                self.IDrectangle = srw.rectangle
                self.IDwhichFile = srw.whichFile
                self.ui.predictButton.setEnabled(True)

    def viewIDPage(self):
        idi = self.ui.predictionTW.selectedIndexes()
        if len(idi) == 0:
            return
        test = int(self.ui.predictionTW.item(idi[0].row(), 0).text())
        sid = int(self.ui.predictionTW.item(idi[0].row(), 1).text())
        imageList = managerMessenger.IDrequestImage(test)
        inames = []
        with tempfile.TemporaryDirectory() as td:
            for i in range(len(imageList)):
                tmp = os.path.join(td, "id.{}.png".format(i))
                inames.append(tmp)
                with open(tmp, "wb+") as fh:
                    fh.write(imageList[i])
            IDViewWindow(self, inames, sid).exec_()

    def runPredictor(self, ignoreStamp=False):
        rmsg = managerMessenger.IDrunPredictions(
            [
                self.IDrectangle.left(),
                self.IDrectangle.top(),
                self.IDrectangle.width(),
                self.IDrectangle.height(),
            ],
            self.IDwhichFile,
            ignoreStamp,
        )
        # returns [True, True] = off and running,
        # [True, False] = currently running.
        # [False, time] = found a timestamp
        if rmsg[0]:
            if rmsg[1]:
                txt = "IDReader launched. It may take some time to run. Please be patient."
            else:
                txt = "IDReader currently running. Please be patient."
            ErrorMessage(txt).exec_()
            return
        else:  # not running because we found a timestamp = rmsg[1]
            sm = SimpleMessage(
                "IDReader was last run at {}. Do you want to rerun it?".format(rmsg[1])
            )
            if sm.exec_() == QMessageBox.No:
                return
            else:
                self.runPredictor(ignoreStamp=True)

    def getPredictions(self):
        csvfile = managerMessenger.IDrequestPredictions()
        pdict = {}
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        for row in reader:
            pdict[int(row["test"])] = str(row["id"])
        iDict = managerMessenger.getIdentified()
        for t in iDict.keys():
            pdict[int(t)] = str(iDict[t][0])

        self.ui.predictionTW.clearContents()
        self.ui.predictionTW.setRowCount(0)
        r = 0
        for t in pdict.keys():
            self.ui.predictionTW.insertRow(r)
            self.ui.predictionTW.setItem(r, 0, QTableWidgetItem("{}".format(t)))
            it = QTableWidgetItem("{}".format(pdict[t]))
            it2 = QTableWidgetItem("")
            if str(t) in iDict:
                it.setBackground(QBrush(Qt.cyan))
                it.setToolTip("Has been identified")
                it2.setText(iDict[str(t)][1])
                it2.setBackground(QBrush(Qt.cyan))
                it2.setToolTip("Has been identified")
            self.ui.predictionTW.setItem(r, 1, it)
            self.ui.predictionTW.setItem(r, 2, it2)
            r += 1

    def deletePredictions(self):
        msg = SimpleMessage(
            "Are you sure you want the server to delete predicted IDs? (note that this does not delete user-inputted IDs)"
        )
        if msg.exec_() == QMessageBox.No:
            return
        managerMessenger.IDdeletePredictions()
        self.getPredictions()

    def initMarkTab(self):
        grid = QGridLayout()
        self.pd = {}
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = managerMessenger.getProgress(q, v)
                self.pd[(q, v)] = ProgressBox(self, q, v, stats)
                grid.addWidget(self.pd[(q, v)], q, v)
        self.ui.markBucket.setLayout(grid)

    def refreshMTab(self):
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = managerMessenger.getProgress(q, v)
                self.pd[(q, v)].refresh(stats)

    def viewMarkHistogram(self, question, version):
        mhist = managerMessenger.getMarkHistogram(question, version)
        QVHistogram(question, version, mhist).exec_()
        # print(mhist)

    def initOutTab(self):
        self.ui.tasksOutTW.setColumnCount(3)
        self.ui.tasksOutTW.setHorizontalHeaderLabels(["Task", "User", "Time"])

    def refreshOutTab(self):
        tasksOut = managerMessenger.RgetOutToDo()
        self.ui.tasksOutTW.clearContents()
        self.ui.tasksOutTW.setRowCount(0)

        if len(tasksOut) == 0:
            ErrorMessage("No tasks out currently.").exec_()
            return

        r = 0
        for x in tasksOut:
            self.ui.tasksOutTW.insertRow(r)
            self.ui.tasksOutTW.setItem(r, 0, QTableWidgetItem(str(x[0])))
            self.ui.tasksOutTW.setItem(r, 1, QTableWidgetItem(str(x[1])))
            self.ui.tasksOutTW.setItem(r, 2, QTableWidgetItem(str(x[2])))
            r += 1

    def todo(self, msg=""):
        ErrorMessage("This is on our to-do list" + msg).exec_()

    def initUnknownTab(self):
        self.unknownModel = QStandardItemModel(0, 6)
        self.ui.unknownTV.setModel(self.unknownModel)
        self.ui.unknownTV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.unknownTV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.unknownModel.setHorizontalHeaderLabels(
            [
                "FullFile",
                "File",
                "Action to be taken",
                "Rotation-angle",
                "Test",
                "Page or Question",
            ]
        )
        self.ui.unknownTV.setIconSize(QSize(96, 96))
        self.ui.unknownTV.activated.connect(self.viewUPage)
        self.ui.unknownTV.setColumnHidden(0, True)
        self.refreshUList()

    def refreshUList(self):
        self.unknownModel.removeRows(0, self.unknownModel.rowCount())
        unkList = managerMessenger.getUnknownPageNames()
        r = 0
        for u in unkList:
            it0 = QStandardItem(os.path.split(u)[1])
            it0.setIcon(QIcon(QPixmap("./icons/manager_unknown.svg")))
            it1 = QStandardItem("?")
            it1.setTextAlignment(Qt.AlignCenter)
            it2 = QStandardItem("0")
            it2.setTextAlignment(Qt.AlignCenter)
            it3 = QStandardItem("")
            it3.setTextAlignment(Qt.AlignCenter)
            it4 = QStandardItem("")
            it4.setTextAlignment(Qt.AlignCenter)
            self.unknownModel.insertRow(r, [QStandardItem(u), it0, it1, it2, it3, it4])
            r += 1
        self.ui.unknownTV.resizeRowsToContents()
        self.ui.unknownTV.resizeColumnsToContents()

    def viewUPage(self):
        pvi = self.ui.unknownTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.unknownModel.item(r, 0).text()
        vp = managerMessenger.getUnknownImage(fname)
        if vp is None:
            return
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(vp)
            uvw = UnknownViewWindow(
                self,
                [fh.name],
                [self.numberOfTests, self.numberOfPages, self.numberOfQuestions],
            )
            if uvw.exec_() == QDialog.Accepted:
                self.unknownModel.item(r, 2).setText(uvw.action)
                self.unknownModel.item(r, 3).setText("{}".format(uvw.theta))
                self.unknownModel.item(r, 4).setText("{}".format(uvw.test))
                self.unknownModel.item(r, 5).setText("{}".format(uvw.pq))
                if uvw.action == "discard":
                    self.unknownModel.item(r, 1).setIcon(
                        QIcon(QPixmap("./icons/manager_discard.svg"))
                    )
                elif uvw.action == "extra":
                    self.unknownModel.item(r, 1).setIcon(
                        QIcon(QPixmap("./icons/manager_extra.svg"))
                    )
                elif uvw.action == "test":
                    self.unknownModel.item(r, 1).setIcon(
                        QIcon(QPixmap("./icons/manager_test.svg"))
                    )

    def doUActions(self):
        for r in range(self.unknownModel.rowCount()):
            if self.unknownModel.item(r, 2).text() == "discard":
                managerMessenger.removeUnknownImage(self.unknownModel.item(r, 0).text())
            elif self.unknownModel.item(r, 2).text() == "extra":
                managerMessenger.unknownToExtraPage(
                    self.unknownModel.item(r, 0).text(),
                    self.unknownModel.item(r, 4).text(),
                    self.unknownModel.item(r, 5).text(),
                    self.unknownModel.item(r, 3).text(),
                )
            elif self.unknownModel.item(r, 2).text() == "test":
                if (
                    managerMessenger.unknownToTestPage(
                        self.unknownModel.item(r, 0).text(),
                        self.unknownModel.item(r, 4).text(),
                        self.unknownModel.item(r, 5).text(),
                        self.unknownModel.item(r, 3).text(),
                    )
                    == "collision"
                ):
                    ErrorMessage(
                        "Collision created in test {}".format(
                            self.unknownModel.item(r, 4).text()
                        )
                    )

            else:
                print(
                    "No action for file {}.".format(self.unknownModel.item(r, 0).text())
                )
        self.refreshUList()

    def viewWholeTest(self, testNumber):
        vt = managerMessenger.getTestImages(testNumber)
        if vt is None:
            return
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i in range(len(vt)):
                iname = td + "img.{}.png".format(i)
                with open(iname, "wb") as fh:
                    fh.write(vt[i])
                inames.append(iname)
            tv = WholeTestView(inames)
            tv.exec_()

    def viewQuestion(self, testNumber, questionNumber):
        vq = managerMessenger.getQuestionImages(testNumber, questionNumber)
        if vq is None:
            return
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i in range(len(vq)):
                iname = td + "img.{}.png".format(i)
                with open(iname, "wb") as fh:
                    fh.write(vq[i])
                inames.append(iname)
            qv = GroupView(inames)
            qv.exec_()

    def checkPage(self, testNumber, pageNumber):
        cp = managerMessenger.checkPage(testNumber, pageNumber)
        # returns [v, image] or [v, imageBytes]
        if cp[1] == None:
            ErrorMessage(
                "Page {} of test {} is not scanned - should be version {}".format(
                    pageNumber, testNumber, cp[0]
                )
            ).exec_()
            return
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(cp[1])
            ErrorMessage(
                "WARNING: potential collision! Page {} of test {} has been scanned already.".format(
                    pageNumber, testNumber
                )
            ).exec_()
            GroupView([fh.name]).exec_()

    def initCollideTab(self):
        self.collideModel = QStandardItemModel(0, 6)
        self.ui.collideTV.setModel(self.collideModel)
        self.ui.collideTV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.collideTV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.collideModel.setHorizontalHeaderLabels(
            ["FullFile", "File", "Action to be taken", "Test", "Page", "Version"]
        )
        self.ui.collideTV.setIconSize(QSize(96, 96))
        self.ui.collideTV.activated.connect(self.viewCPage)
        self.ui.collideTV.setColumnHidden(0, True)
        self.refreshCList()

    def refreshCList(self):
        self.collideModel.removeRows(0, self.collideModel.rowCount())
        colDict = managerMessenger.getCollidingPageNames()  # dict [fname]=[t,p,v]
        r = 0
        for u in colDict.keys():
            it0 = QStandardItem(u)
            it1 = QStandardItem(os.path.split(u)[1])
            it1.setIcon(QIcon(QPixmap("./icons/manager_collide.svg")))
            it2 = QStandardItem("?")
            it2.setTextAlignment(Qt.AlignCenter)
            it3 = QStandardItem("{}".format(colDict[u][0]))
            it3.setTextAlignment(Qt.AlignCenter)
            it4 = QStandardItem("{}".format(colDict[u][1]))
            it4.setTextAlignment(Qt.AlignCenter)
            it5 = QStandardItem("{}".format(colDict[u][2]))
            it5.setTextAlignment(Qt.AlignCenter)
            self.collideModel.insertRow(r, [QStandardItem(u), it1, it2, it3, it4, it5])
            r += 1
        self.ui.collideTV.resizeRowsToContents()
        self.ui.collideTV.resizeColumnsToContents()

    def viewCPage(self):
        pvi = self.ui.collideTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.collideModel.item(r, 0).text()
        test = int(self.collideModel.item(r, 3).text())
        page = int(self.collideModel.item(r, 4).text())
        version = int(self.collideModel.item(r, 5).text())

        vop = managerMessenger.getPageImage(test, page, version)
        vcp = managerMessenger.getCollidingImage(fname)
        if vop is None or vcp is None:
            return
        with tempfile.NamedTemporaryFile() as oh:
            with tempfile.NamedTemporaryFile() as ch:
                oh.write(vop)
                ch.write(vcp)
                cvw = CollideViewWindow(self, oh.name, ch.name, test, page,)
                if cvw.exec_() == QDialog.Accepted:
                    if cvw.action == "original":
                        self.collideModel.item(r, 1).setIcon(
                            QIcon(QPixmap("./icons/manager_discard.svg"))
                        )
                        self.collideModel.item(r, 2).setText("discard")
                    elif cvw.action == "collide":
                        self.collideModel.item(r, 1).setIcon(
                            QIcon(QPixmap("./icons/manager_test.svg"))
                        )
                        self.collideModel.item(r, 2).setText("replace")

    def doCActions(self):
        for r in range(self.collideModel.rowCount()):
            if self.collideModel.item(r, 2).text() == "discard":
                managerMessenger.removeCollidingImage(
                    self.collideModel.item(r, 0).text()
                )
            elif self.collideModel.item(r, 2).text() == "replace":
                managerMessenger.collidingToTestPage(
                    self.collideModel.item(r, 0).text(),
                    self.collideModel.item(r, 3).text(),
                    self.collideModel.item(r, 4).text(),
                    self.collideModel.item(r, 5).text(),
                )
            else:
                print(
                    "No action for file {}.".format(self.collideModel.item(r, 0).text())
                )
        self.refreshCList()

    def initDiscardTab(self):
        self.discardModel = QStandardItemModel(0, 3)
        self.ui.discardTV.setModel(self.discardModel)
        self.ui.discardTV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.discardTV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.discardModel.setHorizontalHeaderLabels(
            ["FullFile", "File", "Action to be taken",]
        )
        self.ui.discardTV.setIconSize(QSize(96, 96))
        self.ui.discardTV.activated.connect(self.viewDPage)
        self.ui.discardTV.setColumnHidden(0, True)
        self.refreshDList()

    def refreshDList(self):
        self.discardModel.removeRows(0, self.discardModel.rowCount())
        disList = managerMessenger.getDiscardNames()  # list
        r = 0
        for u in disList:
            it0 = QStandardItem(u)
            it1 = QStandardItem(os.path.split(u)[1])
            it1.setIcon(QIcon(QPixmap("./icons/manager_none.svg")))
            it2 = QStandardItem("none")
            it2.setTextAlignment(Qt.AlignCenter)
            self.discardModel.insertRow(r, [it0, it1, it2])
            r += 1
        self.ui.discardTV.resizeRowsToContents()
        self.ui.discardTV.resizeColumnsToContents()

    def viewDPage(self):
        pvi = self.ui.discardTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.discardModel.item(r, 0).text()
        vdp = managerMessenger.getDiscardImage(fname)
        if vdp is None:
            return
        with tempfile.NamedTemporaryFile() as dh:
            dh.write(vdp)
            dvw = DiscardViewWindow(self, dh.name)
            if dvw.exec_() == QDialog.Accepted:
                if dvw.action == "unknown":
                    self.discardModel.item(r, 1).setIcon(
                        QIcon(QPixmap("./icons/manager_move.svg"))
                    )
                    self.discardModel.item(r, 2).setText("move")
                elif dvw.action == "none":
                    self.discardModel.item(r, 1).setIcon(
                        QIcon(QPixmap("./icons/manager_none.svg"))
                    )
                    self.discardModel.item(r, 2).setText("none")

    def doDActions(self):
        for r in range(self.discardModel.rowCount()):
            if self.discardModel.item(r, 2).text() == "move":
                managerMessenger.discardToUnknown(self.discardModel.item(r, 0).text())
            else:
                print(
                    "No action for file {}.".format(self.discardModel.item(r, 0).text())
                )
        self.refreshDList()

    def initRevTab(self):
        self.ui.reviewTW.setColumnCount(7)
        self.ui.reviewTW.setHorizontalHeaderLabels(
            ["Test", "Question", "Version", "Mark", "Username", "Marking Time", "When"]
        )
        self.ui.reviewTW.setSortingEnabled(True)
        self.ui.reviewTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.reviewTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.reviewTW.activated.connect(self.reviewAnnotated)

        self.ui.questionCB.addItem("*")
        for q in range(self.numberOfQuestions):
            self.ui.questionCB.addItem(str(q + 1))
        self.ui.versionCB.addItem("*")
        for v in range(self.numberOfVersions):
            self.ui.versionCB.addItem(str(v + 1))
        ulist = managerMessenger.getUserList()
        self.ui.userCB.addItem("*")
        for u in ulist:
            self.ui.userCB.addItem(u)
        self.ui.filterB.clicked.connect(self.filterReview)

    def filterReview(self):
        if (
            (self.ui.questionCB.currentText() == "*")
            and (self.ui.versionCB.currentText() == "*")
            and (self.ui.userCB.currentText() == "*")
        ):
            ErrorMessage(
                'Please set at least one of "Question", "Version", "User" to specific values.'
            ).exec_()
            return
        mrList = managerMessenger.getMarkReview(
            self.ui.questionCB.currentText(),
            self.ui.versionCB.currentText(),
            self.ui.userCB.currentText(),
        )

        self.ui.reviewTW.clearContents()
        self.ui.reviewTW.setRowCount(0)
        r = 0
        for dat in mrList:
            self.ui.reviewTW.insertRow(r)
            # rjust(4) entries so that they can sort like integers... without actually being integers
            for k in range(7):
                self.ui.reviewTW.setItem(
                    r, k, QTableWidgetItem("{}".format(dat[k]).rjust(4))
                )
            if dat[4] == "reviewer":
                for k in range(7):
                    self.ui.reviewTW.item(r, k).setBackground(QBrush(Qt.green))
            r += 1

    def reviewAnnotated(self):
        rvi = self.ui.reviewTW.selectedIndexes()
        if len(rvi) == 0:
            return
        r = rvi[0].row()
        test = int(self.ui.reviewTW.item(r, 0).text())
        question = int(self.ui.reviewTW.item(r, 1).text())
        version = int(self.ui.reviewTW.item(r, 2).text())
        img = managerMessenger.RgetAnnotatedImage(test, question, version)
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(img)
            rvw = ReviewViewWindow(self, [fh.name])
            if rvw.exec() == QDialog.Accepted:
                if rvw.action == "review":
                    # first remove auth from that user - safer.
                    if self.ui.reviewTW.item(r, 4).text() != "reviwer":
                        managerMessenger.clearAuthorisationUser(
                            self.ui.reviewTW.item(r, 4).text()
                        )
                    # then map that question's owner "reviewer"
                    managerMessenger.MreviewQuestion(test, question, version)
                    self.ui.reviewTW.item(r, 4).setText("reviewer")

    def initRevIDTab(self):
        self.ui.reviewIDTW.setColumnCount(5)
        self.ui.reviewIDTW.setHorizontalHeaderLabels(
            ["Test", "Username", "When", "Student ID", "Student Name"]
        )
        self.ui.reviewIDTW.setSortingEnabled(True)
        self.ui.reviewIDTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.reviewIDTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.reviewIDTW.activated.connect(self.reviewIDd)

    def refreshIDRev(self):
        irList = managerMessenger.getIDReview()
        self.ui.reviewIDTW.clearContents()
        self.ui.reviewIDTW.setRowCount(0)
        r = 0
        for dat in irList:
            self.ui.reviewIDTW.insertRow(r)
            # rjust(4) entries so that they can sort like integers... without actually being integers
            for k in range(5):
                self.ui.reviewIDTW.setItem(
                    r, k, QTableWidgetItem("{}".format(dat[k]).rjust(4))
                )
            if dat[1] == "reviewer":
                for k in range(5):
                    self.ui.reviewIDTW.item(r, k).setBackground(QBrush(Qt.green))
            elif dat[1] == "automatic":
                for k in range(5):
                    self.ui.reviewIDTW.item(r, k).setBackground(QBrush(Qt.cyan))
            r += 1

    def reviewIDd(self):
        rvi = self.ui.reviewIDTW.selectedIndexes()
        if len(rvi) == 0:
            return
        r = rvi[0].row()
        # check if ID was computed automatically
        if self.ui.reviewIDTW.item(r, 1).text() == "automatic":
            if (
                SimpleMessage(
                    "This paper was ID'd automatically, are you sure you wish to review it?"
                ).exec_()
                != QMessageBox.Yes
            ):
                return

        test = int(self.ui.reviewIDTW.item(r, 0).text())
        imageList = managerMessenger.IDrequestImage(test)
        inames = []
        with tempfile.TemporaryDirectory() as td:
            for i in range(len(imageList)):
                tmp = os.path.join(td, "id.{}.png".format(i))
                inames.append(tmp)
                with open(tmp, "wb+") as fh:
                    fh.write(imageList[i])
            rvw = ReviewViewWindow(self, inames, "ID pages")
            if rvw.exec() == QDialog.Accepted:
                if rvw.action == "review":
                    # first remove auth from that user - safer.
                    if self.ui.reviewIDTW.item(r, 1).text() != "reviwer":
                        managerMessenger.clearAuthorisationUser(
                            self.ui.reviewIDTW.item(r, 1).text()
                        )
                    # then map that question's owner "reviewer"
                    self.ui.reviewIDTW.item(r, 1).setText("reviewer")
                    managerMessenger.IDreviewID(test)

    def initRevTOTTab(self):
        self.ui.reviewTOTTW.setColumnCount(4)
        self.ui.reviewTOTTW.setHorizontalHeaderLabels(
            ["Test", "Username", "When", "Total Mark"]
        )
        self.ui.reviewTOTTW.setSortingEnabled(True)
        self.ui.reviewTOTTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.reviewTOTTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.reviewTOTTW.activated.connect(self.reviewTotalled)

    def refreshTOTRev(self):
        irList = managerMessenger.getTOTReview()
        self.ui.reviewTOTTW.clearContents()
        self.ui.reviewTOTTW.setRowCount(0)
        r = 0
        for dat in irList:
            self.ui.reviewTOTTW.insertRow(r)
            # rjust(4) entries so that they can sort like integers... without actually being integers
            for k in range(4):
                self.ui.reviewTOTTW.setItem(
                    r, k, QTableWidgetItem("{}".format(dat[k]).rjust(4))
                )
            if dat[1] == "reviewer":
                for k in range(4):
                    self.ui.reviewTOTTW.item(r, k).setBackground(QBrush(Qt.green))
            elif dat[1] == "automatic":
                for k in range(4):
                    self.ui.reviewTOTTW.item(r, k).setBackground(QBrush(Qt.cyan))
            r += 1

    def reviewTotalled(self):
        rvi = self.ui.reviewTOTTW.selectedIndexes()
        if len(rvi) == 0:
            return
        r = rvi[0].row()
        # check if total was computed automatically
        if self.ui.reviewTOTTW.item(r, 1).text() == "automatic":
            if (
                SimpleMessage(
                    "The total was computed automatically, are you sure you wish to review it?"
                ).exec_()
                != QMessageBox.Yes
            ):
                return

        test = int(self.ui.reviewTOTTW.item(r, 0).text())
        image = managerMessenger.TrequestImage(test)
        with tempfile.NamedTemporaryFile() as fh:
            fh.write(image)
            rvw = ReviewViewWindow(self, [fh.name], "Total page")
            if rvw.exec() == QDialog.Accepted:
                if rvw.action == "review":
                    # first remove auth from that user - safer.
                    if self.ui.reviewTOTTW.item(r, 1).text() != "reviwer":
                        managerMessenger.clearAuthorisationUser(
                            self.ui.reviewTOTTW.item(r, 1).text()
                        )
                    # then map that question's owner "reviewer"
                    self.ui.reviewTOTTW.item(r, 1).setText("reviewer")
                    managerMessenger.TreviewTOT(test)

    def initUserListTab(self):
        self.ui.userListTW.setColumnCount(5)
        self.ui.userListTW.setHorizontalHeaderLabels(
            [
                "Username",
                "Logged in",
                "Papers IDd",
                "Papers Totalled",
                "Questions Marked",
            ]
        )
        self.ui.userListTW.setSortingEnabled(True)
        self.ui.userListTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.userListTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.ui.userListTW.activated.connect()

    def forceLogout(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return
        r = ri[0].row()
        user = self.ui.userListTW.item(r, 0).text()
        if (
            SimpleMessage(
                'Are you sure you want to force-logout user "{}"?'.format(user)
            ).exec_()
            == QMessageBox.Yes
        ):
            managerMessenger.clearAuthorisationUser(user)

    def refreshUserList(self):
        uDict = managerMessenger.getUserDetails()
        self.ui.userListTW.clearContents()
        self.ui.userListTW.setRowCount(0)
        r = 0
        for u in uDict:
            dat = uDict[u]
            self.ui.userListTW.insertRow(r)
            # rjust(4) entries so that they can sort like integers... without actually being integers
            self.ui.userListTW.setItem(r, 0, QTableWidgetItem("{}".format(u)))
            for k in range(4):
                self.ui.userListTW.setItem(
                    r, k + 1, QTableWidgetItem("{}".format(dat[k]))
                )
            if dat[0]:
                self.ui.userListTW.item(r, 1).setBackground(QBrush(Qt.green))
            if u in ["manager", "scanner", "reviewer"]:
                self.ui.userListTW.item(r, 0).setBackground(QBrush(Qt.green))

            r += 1

    def initQPUTab(self):
        self.ui.QPUserTW.setColumnCount(5)
        self.ui.QPUserTW.setHeaderLabels(
            ["Question", "Version", "User", "Number Marked", "Percentage of Q/V marked"]
        )
        # self.ui.QPUserTW.setSortingEnabled(True)
        self.ui.QPUserTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.QPUserTW.setSelectionBehavior(QAbstractItemView.SelectRows)

    def initPUQTab(self):
        self.ui.PUQTW.setColumnCount(5)
        self.ui.PUQTW.setHeaderLabels(
            ["User", "Question", "Version", "Number Marked", "Percentage of Q/V marked"]
        )
        # self.ui.PUQTW.setSortingEnabled(True)
        self.ui.PUQTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.PUQTW.setSelectionBehavior(QAbstractItemView.SelectRows)

    def refreshQPU(self):
        # delete the children of each toplevel items
        root = self.ui.QPUserTW.invisibleRootItem()
        for l0 in range(self.ui.QPUserTW.topLevelItemCount()):
            l0i = self.ui.QPUserTW.topLevelItem(0)
            for l1 in range(self.ui.QPUserTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        r = 0
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                qpu = managerMessenger.getQuestionUserProgress(q, v)
                l0 = QTreeWidgetItem([str(q).rjust(4), str(v).rjust(2)])
                for (u, n) in qpu[1:]:
                    pb = QProgressBar()
                    pb.setMaximum(qpu[0])
                    pb.setValue(n)
                    l1 = QTreeWidgetItem(["", "", str(u), str(n).rjust(4)])
                    l0.addChild(l1)
                    self.ui.QPUserTW.setItemWidget(l1, 4, pb)
                self.ui.QPUserTW.addTopLevelItem(l0)

    def refreshPUQ(self):
        # delete the children of each toplevel items
        root = self.ui.PUQTW.invisibleRootItem()
        for l0 in range(self.ui.PUQTW.topLevelItemCount()):
            l0i = self.ui.PUQTW.topLevelItem(0)
            for l1 in range(self.ui.PUQTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        # get list of everything done by users
        uprog = defaultdict(list)
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                qpu = managerMessenger.getQuestionUserProgress(q, v)
                for (u, n) in qpu[1:]:
                    uprog[u].append(
                        [q, v, n, qpu[0]]
                    )  # question, version, no marked, no total

        for u in uprog:
            l0 = QTreeWidgetItem([str(u)])
            for qvn in uprog[u]:  # will be in q,v,n,ntot in qv order
                pb = QProgressBar()
                pb.setMaximum(qvn[3])
                pb.setValue(qvn[2])
                l1 = QTreeWidgetItem(
                    ["", str(qvn[0]).rjust(4), str(qvn[1]).rjust(2), str(n).rjust(4)]
                )
                l0.addChild(l1)
                self.ui.PUQTW.setItemWidget(l1, 4, pb)
            self.ui.PUQTW.addTopLevelItem(l0)
