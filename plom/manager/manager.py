# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021-2022 Elizabeth Xiao

from collections import defaultdict
import csv
import imghdr
import logging
import os
from pathlib import Path
import sys
import tempfile

import arrow
import urllib3

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QBrush, QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidgetItem,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import plom.client.icons

from plom.client.useful_classes import ErrorMessage, WarnMsg
from plom.client.useful_classes import SimpleQuestion, WarningQuestion
from plom.client.origscanviewer import WholeTestView, GroupView
from plom.client import ImageViewWidget

from .uiFiles.ui_manager import Ui_Manager
from .unknownpageview import UnknownViewWindow
from .collideview import CollideViewWindow
from .discardview import DiscardViewWindow
from .reviewview import ReviewViewWindow
from .selectrectangle import SelectRectangleWindow, IDViewWindow
from plom.plom_exceptions import (
    PlomSeriousException,
    PlomAPIException,
    PlomAuthenticationException,
    PlomBenignException,
    PlomConflict,
    PlomExistingLoginException,
    PlomOwnersLoggedInException,
    PlomUnidentifiedPaperException,
    PlomTakenException,
    PlomNoMoreException,
    PlomNoSolutionException,
)
from plom.plom_exceptions import PlomException
from plom.messenger import ManagerMessenger
from plom.aliceBob import simple_password

from plom import __version__, Plom_API_Version, Default_Port


log = logging.getLogger("manager")


class UserDialog(QDialog):
    """Simple dialog to enter username and password"""

    def __init__(self, name=None, extant=[]):
        super().__init__()
        self.name = name
        self.initUI()
        if name is not None:
            self.userLE.setEnabled(False)
        self.extant = [
            x.lower() for x in extant
        ]  # put everything in lowercase to simplify checking.

    def initUI(self):
        self.setWindowTitle("Please enter user")
        self.userL = QLabel("Username:")
        self.pwL = QLabel("Password:")
        self.pwL2 = QLabel("and again:")
        self.userLE = QLineEdit(self.name)
        initialpw = simple_password()
        self.pwLE = QLineEdit(initialpw)
        # self.pwLE.setEchoMode(QLineEdit.Password)
        self.pwLE2 = QLineEdit(initialpw)
        self.pwLE2.setEchoMode(QLineEdit.Password)
        self.okB = QPushButton("Accept")
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton("Cancel")
        self.cnB.clicked.connect(self.reject)

        self.pwCB = QCheckBox("(hide/show)")
        self.pwCB.setCheckState(Qt.Unchecked)
        self.pwCB.stateChanged.connect(self.togglePWShow)
        self.pwNewB = QPushButton("New rand pwd")
        self.pwNewB.clicked.connect(self.newRandomPassword)

        grid = QGridLayout()
        grid.addWidget(self.userL, 1, 1)
        grid.addWidget(self.userLE, 1, 2)
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwCB, 2, 3)
        grid.addWidget(self.pwNewB, 3, 3)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.okB, 4, 3)
        grid.addWidget(self.cnB, 4, 1)

        self.setLayout(grid)
        self.show()

    def togglePWShow(self):
        if self.pwCB.checkState() == Qt.Checked:
            self.pwLE.setEchoMode(QLineEdit.Password)
        else:
            self.pwLE.setEchoMode(QLineEdit.Normal)

    def newRandomPassword(self):
        newpw = simple_password()
        self.pwLE.setText(newpw)
        self.pwLE2.setText(newpw)

    def validate(self):
        """Check username not in list and that passwords match."""
        # username not already in list
        # be careful, because pwd-change users same interface
        # make sure that we only do this check if the LE is enabled.
        # put username into lowercase to check against extant which is in lowercase.
        if self.userLE.isEnabled() and self.userLE.text().lower() in self.extant:
            ErrorMessage(
                "Username = '{}' already in user list".format(self.userLE.text())
            ).exec_()
            return

        if self.pwLE.text() != self.pwLE2.text():
            ErrorMessage("Passwords do not match").exec_()
            return
        self.name = self.userLE.text()
        self.password = self.pwLE.text()
        self.accept()


class QVHistogram(QDialog):
    def __init__(self, q, v, hist):
        super().__init__()
        self.question = q
        self.version = v
        self.setWindowTitle("Histograms for question {} version {}".format(q, v))
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

        grid = QGridLayout()

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
        grid.addWidget(self.eG, 0, 0)

        max_number_of_rows = 4  # should depend on user's viewport
        current_row = 1
        current_column = 0

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
            grid.addWidget(self.uG[u], current_row, current_column)
            current_row = (current_row + 1) % max_number_of_rows
            if current_row == 0:
                current_column = current_column + 1

        self.cB = QPushButton("&Close")
        self.cB.clicked.connect(self.accept)
        grid.addWidget(self.cB)
        self.setLayout(grid)
        self.show()


class TestStatus(QDialog):
    def __init__(self, nq, status):
        super().__init__()
        self.status = status
        self.setWindowTitle("Status of test {}".format(self.status["number"]))

        grid = QGridLayout()
        self.idCB = QCheckBox("Identified: ")
        self.idCB.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.idCB.setFocusPolicy(Qt.NoFocus)
        if status["identified"]:
            self.idCB.setCheckState(Qt.Checked)
        self.mkCB = QCheckBox("Marked: ")
        self.mkCB.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.mkCB.setFocusPolicy(Qt.NoFocus)
        if status["marked"]:
            self.mkCB.setCheckState(Qt.Checked)

        self.clB = QPushButton("&close")
        self.clB.clicked.connect(self.accept)

        grid.addWidget(self.idCB, 1, 1)
        grid.addWidget(self.mkCB, 1, 3)

        if status["identified"]:
            self.iG = QGroupBox("Identification")
            gg = QVBoxLayout()
            gg.addWidget(QLabel("ID: {}".format(status["sid"])))
            gg.addWidget(QLabel("Name: {}".format(status["sname"])))
            gg.addWidget(QLabel("Username: {}".format(status["iwho"])))
            self.iG.setLayout(gg)
            grid.addWidget(self.iG, 2, 1, 3, 3)

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
        super().__init__(parent)
        self._parent = parent
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
        self.mmfL = QLabel()
        grid.addWidget(self.mmfL)

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
        self.setVisible(True)
        self.pb.setMaximum(self.stats["NScanned"])
        self.pb.setValue(self.stats["NMarked"])
        self.nscL.setText("# Scanned = {}".format(self.stats["NScanned"]))
        self.nmkL.setText("# Marked = {}".format(self.stats["NMarked"]))

        if self.stats["NScanned"] == 0:
            self.setEnabled(False)
            self.setVisible(False)
            return
        if self.stats["NMarked"] > 0:
            self.avgL.setText(
                "Mean : Median : Mode = {:0.2f} : {} : {}".format(
                    self.stats["avgMark"],
                    self.stats["medianMark"],
                    self.stats["modeMark"],
                )
            )
            self.mmfL.setText(
                "Min : Max : Full = {} : {} : {}".format(
                    self.stats["minMark"], self.stats["maxMark"], self.stats["fullMark"]
                )
            )
            self.mtL.setText(
                "Avg marking time = {:0.1f}s".format(self.stats["avgMTime"])
            )
            self.lhL.setText("# Marked in last hour = {}".format(self.stats["NRecent"]))
        else:
            self.avgL.setText("Mean : Median : Mode  = N/A")
            self.mmfL.setText(
                "Min : Max : Full = N/A : N/A : {}".format(self.stats["fullMark"])
            )
            self.mtL.setText("Avg marking time = N/A")
            self.lhL.setText("# Marked in last hour = N/A")

    def viewHist(self):
        self._parent.viewMarkHistogram(self.question, self.version)


class Manager(QWidget):
    def __init__(
        self, Qapp, *, server=None, user=None, password=None, manager_msgr=None
    ):
        """Start a new Plom Manager window.

        Args:
            Qapp (QApplication):

        Keyword Args:
            manager_msgr (ManagerMessenger/None): a connected ManagerMessenger.
                Note that the plain 'ol Messenger will not work.  By default
                or if `None` is passed, we'll make the user login or use
                other kwargs.
            server (str/None):
            user (str/None):
            password (str/None):
        """
        self.APIVersion = Plom_API_Version
        super().__init__()
        self.Qapp = Qapp
        self.msgr = manager_msgr
        print(
            "Plom Manager Client {} (communicates with api {})".format(
                __version__, self.APIVersion
            )
        )
        self.ui = Ui_Manager()
        self.ui.setupUi(self)
        if user:
            self.ui.userLE.setText(user)
        if password:
            self.ui.passwordLE.setText(password)
        if server:
            self.setServer(server)

        self.ui.passwordLE.setFocus(True)
        self.connectButtons()
        self.ui.scanningAllTab.setEnabled(False)
        self.ui.progressAllTab.setEnabled(False)
        self.ui.reviewAllTab.setEnabled(False)
        self.ui.userAllTab.setEnabled(False)
        if self.msgr:
            self.initial_login()
        else:
            if password:
                self.login()

    def connectButtons(self):
        self.ui.loginButton.clicked.connect(self.login)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.fontSB.valueChanged.connect(self.setFont)
        self.ui.scanRefreshB.clicked.connect(self.refreshScanTab)
        self.ui.progressRefreshB.clicked.connect(self.refreshProgressTab)
        self.ui.refreshIDPredictionsB.clicked.connect(self.getPredictions)
        self.ui.unidB.clicked.connect(self.un_id_paper)

        self.ui.refreshRevB.clicked.connect(self.refreshRev)
        self.ui.refreshUserB.clicked.connect(self.refreshUserList)
        self.ui.refreshProgressQUB.clicked.connect(self.refreshProgressQU)

        self.ui.removePagesB.clicked.connect(self.removePages)
        self.ui.subsPageB.clicked.connect(self.substitutePage)
        self.ui.removePartScanB.clicked.connect(self.removePagesFromPartScan)
        self.ui.removeDanglingB.clicked.connect(self.removeDanglingPage)

        self.ui.actionUButton.clicked.connect(self.doUActions)
        self.ui.actionCButton.clicked.connect(self.doCActions)
        self.ui.actionDButton.clicked.connect(self.doDActions)
        self.ui.selectRectButton.clicked.connect(self.selectRectangle)
        self.ui.predictButton.clicked.connect(self.runPredictor)
        self.ui.delPredButton.clicked.connect(self.deletePredictions)
        self.ui.forceLogoutB.clicked.connect(self.forceLogout)
        self.ui.enableUserB.clicked.connect(self.enableUsers)
        self.ui.disableUserB.clicked.connect(self.disableUsers)
        self.ui.changePassB.clicked.connect(self.changeUserPassword)
        self.ui.newUserB.clicked.connect(self.createUser)

    def closeEvent(self, event):
        log.debug("Something has triggered a shutdown event")
        log.debug("Revoking login token")
        try:
            if self.msgr:
                self.msgr.closeUser()
        except PlomAuthenticationException:
            log.warn("User tried to logout but was already logged out.")
            pass
        event.accept()

    def setServer(self, s):
        """Set the server and port UI widgets from a string.

        If port is missing, a default will be used."""
        try:
            s, p = s.split(":")
        except ValueError:
            p = Default_Port
        self.ui.serverLE.setText(s)
        self.ui.mportSB.setValue(int(p))

    def setFont(self, n):
        fnt = self.Qapp.font()
        fnt.setPointSize(n)
        self.Qapp.setFont(fnt)

    def login(self):
        user = self.ui.userLE.text().strip()
        self.ui.userLE.setText(user)
        if not user:
            return
        pwd = self.ui.passwordLE.text()
        if not pwd:
            return

        self.partial_parse_address()
        server = self.ui.serverLE.text()
        self.ui.serverLE.setText(server)
        mport = self.ui.mportSB.value()

        try:
            self.msgr = ManagerMessenger(server, mport)
            self.msgr.start()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n{}".format(e)).exec_()
            self.msgr = None  # reset to avoid Issue #1622
            return

        try:
            self.msgr.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            ErrorMessage(
                "Could not authenticate due to API mismatch."
                "Your client version is {}.\n\n"
                "Error was: {}".format(__version__, e)
            ).exec_()
            self.msgr = None  # reset to avoid Issue #1622
            return
        except PlomExistingLoginException:
            if (
                SimpleQuestion(
                    self,
                    "You appear to be already logged in!\n\n"
                    "  * Perhaps a previous session crashed?\n"
                    "  * Do you have another client running,\n"
                    "    e.g., on another computer?\n\n"
                    "Should I force-logout the existing authorisation?"
                    " (and then you can try to log in again)\n\n"
                    "The other client will likely crash.",
                ).exec_()
                == QMessageBox.Yes
            ):
                self.msgr.clearAuthorisation("manager", pwd)
            self.msgr = None  # reset to avoid Issue #1622
            return
        except PlomAuthenticationException as e:
            ErrorMessage("Could not authenticate: {}".format(e)).exec_()
            self.msgr = None  # reset to avoid Issue #1622
            return
        except PlomSeriousException as e:
            ErrorMessage(
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e)
            ).exec_()
            self.msgr = None  # reset to avoid Issue #1622
            return
        self.initial_login()

    def initial_login(self):
        self.ui.scanningAllTab.setEnabled(True)
        self.ui.progressAllTab.setEnabled(True)
        self.ui.reviewAllTab.setEnabled(True)
        self.ui.userAllTab.setEnabled(True)

        self.ui.userGBox.setEnabled(False)
        self.ui.serverGBox.setEnabled(False)
        self.ui.loginButton.setEnabled(False)

        self.getTPQV()
        self.initScanTab()
        self.initProgressTab()
        self.initUserTab()
        self.initReviewTab()
        self.initSolutionTab()

    def partial_parse_address(self):
        """If address has a port number in it, extract and move to the port box.

        If there's a colon in the address (maybe user did not see port
        entry box or is pasting in a string), then try to extract a port
        number and put it into the entry box.
        """
        address = self.ui.serverLE.text()
        try:
            parsedurl = urllib3.util.parse_url(address)
            if parsedurl.port:
                self.ui.mportSB.setValue(int(parsedurl.port))
            self.ui.serverLE.setText(parsedurl.host)
        except urllib3.exceptions.LocationParseError:
            return

    # -------------------
    def getTPQV(self):
        info = self.msgr.get_spec()
        self.max_papers = info["numberToProduce"]
        self.numberOfPages = info["numberOfPages"]
        self.numberOfQuestions = info["numberOfQuestions"]
        self.numberOfVersions = info["numberOfVersions"]
        # which test pages are which type "id", "dnm", or "qN"
        self.testPageTypes = {info["idPage"]: "id"}
        for pg in info["doNotMarkPages"]:
            self.testPageTypes[pg] = "dnm"
        for q in range(1, info["numberOfQuestions"] + 1):
            for pg in info["question"][str(q)]["pages"]:
                self.testPageTypes[pg] = f"q{q}"

    ################
    # scan tab stuff

    def initScanTab(self):
        self.initScanStatusTab()
        self.initUnknownTab()
        self.initCollideTab()
        self.initDiscardTab()
        self.initDanglingTab()

    def refreshScanTab(self):
        self.refresh_scan_status_lists()
        self.refreshUList()
        self.refreshCList()
        self.refreshDList()
        self.refreshDangList()

    def initScanStatusTab(self):
        self.ui.scanTW.setHeaderLabels(["Test number", "Page number", "Version"])
        self.ui.scanTW.activated.connect(self.viewSPage)
        self.ui.incompTW.setHeaderLabels(["Test number", "Page", "Version", "Status"])
        self.ui.incompTW.activated.connect(self.viewISTest)
        self.refresh_scan_status_lists()

    def refresh_scan_status_lists(self):
        I = self._refreshIList()
        S = self._refreshSList()
        countstr = str(I + S)
        countstr += "*" if I != 0 else "\N{check mark}"
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.scanTab),
            f"&Scan Status ({countstr})",
        )

    def _refreshIList(self):
        # delete the children of each toplevel items
        root = self.ui.incompTW.invisibleRootItem()
        for l0 in range(self.ui.incompTW.topLevelItemCount()):
            l0i = self.ui.incompTW.topLevelItem(0)
            for l1 in range(self.ui.incompTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        incomplete = self.msgr.getIncompleteTests()  # triples [p,v,true/false]
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

        self.ui.groupBox_3.setTitle(
            "Incomplete papers (total: {})".format(len(incomplete))
        )
        return len(incomplete)

    def _refreshSList(self):
        # delete the children of each toplevel items
        root = self.ui.scanTW.invisibleRootItem()
        for l0 in range(self.ui.scanTW.topLevelItemCount()):
            l0i = self.ui.scanTW.topLevelItem(0)
            for l1 in range(self.ui.scanTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)

        scanned = self.msgr.getScannedTests()  # pairs [p,v]
        colDict = self.msgr.getCollidingPageNames()  # dict [fname]=[t,p,v]
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

        self.ui.groupBox.setTitle(
            "Completely scanned papers (total: {})".format(len(scanned))
        )
        return len(scanned)

    def viewPage(self, t, pdetails, v):
        if pdetails[0] == "t":  # is a test-page t.PPP
            p = pdetails.split(".")[1]
            vp = self.msgr.getTPageImage(t, p, v)
        elif pdetails[0] == "h":  # is a hw-page = h.q.o
            q = pdetails.split(".")[1]
            o = pdetails.split(".")[2]
            vp = self.msgr.getHWPageImage(t, q, o)
        elif pdetails[0] == "e":  # is a extra-page = e.q.o
            q = pdetails.split(".")[1]
            o = pdetails.split(".")[2]
            vp = self.msgr.getEXPageImage(t, q, o)
        else:
            return

        if vp is None:
            return
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(vp)
        GroupView(self, [f]).exec_()
        f.unlink()

    def viewSPage(self):
        pvi = self.ui.scanTW.selectedItems()
        if len(pvi) == 0:
            return
        # if selected a top-level item (ie a test) - view the whole test
        if pvi[0].childCount() > 0:
            pt = int(pvi[0].text(0))
            self.viewWholeTest(pt)
            return
        pdetails = pvi[0].text(1)
        pv = int(pvi[0].text(2))
        pt = int(pvi[0].parent().text(0))  # grab test number from parent
        self.viewPage(pt, pdetails, pv)

    def viewISTest(self):
        pvi = self.ui.incompTW.selectedItems()
        if len(pvi) == 0:
            return
        # if selected a lower-level item (ie a missing page) - check if scanned
        if pvi[0].childCount() == 0:
            if pvi[0].text(3) == "scanned":
                self.viewPage(
                    int(pvi[0].parent().text(0)),
                    pvi[0].text(1),
                    int(pvi[0].text(2)),
                )
            return
        # else fire up the whole test.
        self.viewWholeTest(int(pvi[0].text(0)))

    def removePages(self):
        pvi = self.ui.scanTW.selectedItems()
        # if nothing selected - return
        if len(pvi) == 0:
            return
        # if selected not a top-level item (ie a test) - return
        if pvi[0].childCount() == 0:
            test_number = int(pvi[0].parent().text(0))
            page_name = pvi[0].text(1)
            msg = WarningQuestion(
                self,
                f"Will remove the selected page {page_name} from the selected test {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec_() == QMessageBox.No:
                return
            try:
                rval = self.msgr.removeSinglePage(test_number, page_name)
                ErrorMessage("{}".format(rval)).exec_()
            except PlomOwnersLoggedInException as err:
                ErrorMessage(
                    "Cannot remove scanned pages from that test - owners of tasks in that test are logged in: {}".format(
                        err.args[-1]
                    )
                ).exec_()
        else:
            test_number = int(pvi[0].text(0))  # grab test number
            msg = WarningQuestion(
                self,
                f"Will remove all scanned pages from the selected test - test number {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec_() == QMessageBox.No:
                return
            try:
                rval = self.msgr.removeAllScannedPages(test_number)
                ErrorMessage("{}".format(rval)).exec_()
            except PlomOwnersLoggedInException as err:
                ErrorMessage(
                    "Cannot remove scanned pages from that test - owners of tasks in that test are logged in: {}".format(
                        err.args[-1]
                    )
                ).exec_()
        self.refresh_scan_status_lists()

    def substituteTestQuestionPage(self, test_number, page_number, question, version):
        msg = SimpleQuestion(
            self,
            'Are you sure you want to substitute a "Missing Page" blank for '
            f"tpage {page_number} of question {question} test {test_number}?",
        )
        if msg.exec_() == QMessageBox.No:
            return
        try:
            rval = self.msgr.replaceMissingTestPage(test_number, page_number, version)
            ErrorMessage("{}".format(rval)).exec_()
        except PlomOwnersLoggedInException as err:
            ErrorMessage(
                "Cannot substitute that page - owners of tasks in that test are logged in: {}".format(
                    err.args[-1]
                )
            ).exec_()

    def substituteTestDNMPage(self, test_number, page_number):
        msg = SimpleQuestion(
            self,
            'Are you sure you want to substitute a "Missing Page" blank for '
            f"tpage {page_number} of test {test_number} - it is a Do Not Mark page?",
        )
        if msg.exec_() == QMessageBox.No:
            return
        try:
            rval = self.msgr.replaceMissingDNMPage(test_number, page_number)
            ErrorMessage("{}".format(rval)).exec_()
        except PlomOwnersLoggedInException as err:
            ErrorMessage(
                "Cannot substitute that page - owners of tasks in that test are logged in: {}".format(
                    err.args[-1]
                )
            ).exec_()

    def autogenerateIDPage(self, test_number):
        msg = SimpleQuestion(
            self,
            f"Are you sure you want to generate an ID for test {test_number}? "
            "You can only do this for homeworks or pre-named tests.",
        )
        if msg.exec_() == QMessageBox.No:
            return
        try:
            rval = self.msgr.replaceMissingIDPage(test_number)
            ErrorMessage("{}".format(rval)).exec_()
        except PlomOwnersLoggedInException as err:
            ErrorMessage(
                "Cannot substitute that page - owners of tasks in that test are logged in: {}".format(
                    err.args[-1]
                )
            ).exec_()
        except PlomUnidentifiedPaperException as err:
            ErrorMessage(
                "Cannot substitute that page - that paper has not been identified: {}".format(
                    err
                )
            ).exec_()

    def substituteTestPage(self, test_number, page_number, version):
        page_type = self.testPageTypes[page_number]
        if page_type == "id":
            self.autogenerateIDPage(test_number)
        elif page_type == "dnm":
            self.substituteTestDNMPage(test_number, page_number)
        else:
            qnum = int(page_type[1:])  # is qNNN
            self.substituteTestQuestionPage(test_number, page_number, qnum, version)

        self.refresh_scan_status_lists()

    def substituteHWQuestion(self, test_number, question):
        msg = SimpleQuestion(
            self,
            'Are you sure you want to substitute a "Missing Page" blank for '
            f"question {question} of test {test_number}?",
        )
        if msg.exec_() == QMessageBox.No:
            return
        try:
            rval = self.msgr.replaceMissingHWQuestion(
                student_id=None, test=test_number, question=question
            )
            ErrorMessage("{}".format(rval)).exec_()
        except PlomTakenException:
            ErrorMessage("That question already has hw pages present.").exec_()
        except PlomOwnersLoggedInException as err:
            ErrorMessage(
                "Cannot substitute that question - owners of tasks in that test are logged in: {}".format(
                    err.args[-1]
                )
            ).exec_()

        self.refresh_scan_status_lists()

    def substitutePage(self):
        # THIS SHOULD KEEP VERSION INFORMATION
        pvi = self.ui.incompTW.selectedItems()
        # if nothing selected - return
        if len(pvi) == 0:
            return
        # if selected a top-level item (ie a test) - return
        if pvi[0].childCount() > 0:
            return
        # text should be t.n - else is homework page
        if pvi[0].text(1)[0] == "t":
            # format = t.n where n = pagenumber
            page = int(pvi[0].text(1)[2:])  # drop the "t."
            version = int(pvi[0].text(2))
            test = int(pvi[0].parent().text(0))  # grab test number from parent
            self.substituteTestPage(test, page, version)
            return
        elif pvi[0].text(1)[0] == "h":
            # format is h.n.k where n= question, k = order
            test = int(pvi[0].parent().text(0))  # grab test number from parent
            question, order = pvi[0].text(1)[2:].split(".")
            # drop the "h.", then split on "." - don't need 'order'
            self.substituteHWQuestion(test, int(question))
        else:  # can't substitute other sorts of pages
            return

    def removePagesFromPartScan(self):
        pvi = self.ui.incompTW.selectedItems()
        # if nothing selected - return
        if len(pvi) == 0:
            return
        # if selected not a top-level item (ie a test) - return
        if pvi[0].childCount() == 0:
            test_number = int(pvi[0].parent().text(0))
            page_name = pvi[0].text(1)
            msg = WarningQuestion(
                self,
                f"Will remove the selected page {page_name} from the selected test {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec_() == QMessageBox.No:
                return
            try:
                rval = self.msgr.removeSinglePage(test_number, page_name)
                ErrorMessage("{}".format(rval)).exec_()
            except PlomOwnersLoggedInException as err:
                ErrorMessage(
                    "Cannot remove scanned pages from that test - owners of tasks in that test are logged in: {}".format(
                        err.args[-1]
                    )
                ).exec_()
        else:
            test_number = int(pvi[0].text(0))  # grab test number
            msg = WarningQuestion(
                self,
                f"Will remove all scanned pages from the selected test - test number {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec_() == QMessageBox.No:
                return
            try:
                rval = self.msgr.removeAllScannedPages(test_number)
                ErrorMessage("{}".format(rval)).exec_()
            except PlomOwnersLoggedInException as err:
                ErrorMessage(
                    "Cannot remove scanned pages from that test - owners of tasks in that test are logged in: {}".format(
                        err.args[-1]
                    )
                ).exec_()
        self.refresh_scan_status_lists()

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
        unkList = self.msgr.getUnknownPageNames()
        r = 0
        for u in unkList:
            it0 = QStandardItem(os.path.split(u)[1])
            pm = QPixmap()
            pm.loadFromData(
                resources.read_binary(plom.client.icons, "manager_unknown.svg")
            )
            it0.setIcon(QIcon(pm))
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

        countstr = str(len(unkList))
        countstr += "*" if countstr != "0" else "\N{Check Mark}"
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.unknownTab),
            f"&Unknown Pages ({countstr})",
        )

    def viewUPage(self):
        pvi = self.ui.unknownTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.unknownModel.item(r, 0).text()
        vp = self.msgr.getUnknownImage(fname)
        if vp is None:
            return
        # get the list of ID'd papers
        iDict = self.msgr.getIdentified()
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(vp)
        if True:  # temp, minimise diff
            uvw = UnknownViewWindow(
                self,
                [f],
                [self.max_papers, self.numberOfPages, self.numberOfQuestions],
                iDict,
            )
            if uvw.exec_() == QDialog.Accepted:
                self.unknownModel.item(r, 2).setText(uvw.action)
                self.unknownModel.item(r, 3).setText("{}".format(uvw.theta))
                self.unknownModel.item(r, 4).setText("{}".format(uvw.test))
                # questions is now of the form "1" or "1,2" or "1,2,3" etc
                self.unknownModel.item(r, 5).setText("{}".format(uvw.pq))
                if uvw.action == "discard":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_discard.svg")
                    )
                    self.unknownModel.item(r, 1).setIcon(QIcon(pm))
                elif uvw.action == "extra":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_extra.svg")
                    )
                    self.unknownModel.item(r, 1).setIcon(QIcon(pm))
                elif uvw.action == "test":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_test.svg")
                    )
                    self.unknownModel.item(r, 1).setIcon(QIcon(pm))
                elif uvw.action == "homework":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_hw.svg")
                    )
                    self.unknownModel.item(r, 1).setIcon(QIcon(pm))
        f.unlink()

    def doUActions(self):
        for r in range(self.unknownModel.rowCount()):
            if self.unknownModel.item(r, 2).text() == "discard":
                self.msgr.removeUnknownImage(self.unknownModel.item(r, 0).text())
            elif self.unknownModel.item(r, 2).text() == "extra":
                try:
                    # have to convert "1,2,3" into [1,2,3]
                    question_list = [
                        int(x) for x in self.unknownModel.item(r, 5).text().split(",")
                    ]
                    self.msgr.unknownToExtraPage(
                        self.unknownModel.item(r, 0).text(),
                        self.unknownModel.item(r, 4).text(),
                        question_list,
                        self.unknownModel.item(r, 3).text(),
                    )
                except (PlomOwnersLoggedInException, PlomConflict) as err:
                    ErrorMessage(f"{err}").exec_()
            elif self.unknownModel.item(r, 2).text() == "test":
                try:
                    if (
                        self.msgr.unknownToTestPage(
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
                        ).exec_()
                except (PlomOwnersLoggedInException, PlomConflict) as err:
                    ErrorMessage(f"{err}").exec_()
            elif self.unknownModel.item(r, 2).text() == "homework":
                try:
                    # have to convert "1,2,3" into [1,2,3]
                    question_list = [
                        int(x) for x in self.unknownModel.item(r, 5).text().split(",")
                    ]
                    self.msgr.unknownToHWPage(
                        self.unknownModel.item(r, 0).text(),
                        self.unknownModel.item(r, 4).text(),
                        question_list,
                        self.unknownModel.item(r, 3).text(),
                    )
                except (PlomOwnersLoggedInException, PlomConflict) as err:
                    ErrorMessage(f"{err}").exec_()

            else:
                pass
                # print(
                #     "No action for file {}.".format(self.unknownModel.item(r, 0).text())
                # )
        self.refreshScanTab()

    def viewWholeTest(self, testNumber, parent=None):
        vt = self.msgr.getTestImages(testNumber)
        if vt is None:
            return
        if parent is None:
            parent = self
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i, img_bytes in enumerate(vt):
                img_ext = imghdr.what(None, h=img_bytes)
                iname = Path(td) / f"img.{i}.{img_ext}"
                with open(iname, "wb") as fh:
                    fh.write(img_bytes)
                inames.append(iname)
            WholeTestView(testNumber, inames, parent=parent).exec_()

    def viewQuestion(self, testNumber, questionNumber, parent=None):
        vq = self.msgr.getQuestionImages(testNumber, questionNumber)
        if vq is None:
            return
        if parent is None:
            parent = self
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i, img_bytes in enumerate(vq):
                img_ext = imghdr.what(None, h=img_bytes)
                iname = Path(td) / f"img.{i}.{img_ext}"
                with open(iname, "wb") as fh:
                    fh.write(img_bytes)
                inames.append(iname)
            GroupView(parent, inames).exec_()

    def checkTPage(self, testNumber, pageNumber, parent=None):
        if parent is None:
            parent = self
        cp = self.msgr.checkTPage(testNumber, pageNumber)
        # returns [v, image] or [v, imageBytes]
        if cp[1] is None:
            # TODO: ErrorMesage does not support parenting
            ErrorMessage(
                "Page {} of test {} is not scanned - should be version {}".format(
                    pageNumber, testNumber, cp[0]
                )
            ).exec_()
            return
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(cp[1])
        ErrorMessage(
            "WARNING: potential collision! Page {} of test {} has been scanned already.".format(
                pageNumber, testNumber
            )
        ).exec_()
        GroupView(parent, [f]).exec_()
        f.unlink()

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
        colDict = self.msgr.getCollidingPageNames()  # dict [fname]=[t,p,v]
        r = 0
        for u in colDict.keys():
            # it0 = QStandardItem(u)
            it1 = QStandardItem(os.path.split(u)[1])
            pm = QPixmap()
            pm.loadFromData(
                resources.read_binary(plom.client.icons, "manager_collide.svg")
            )
            it1.setIcon(QIcon(pm))
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
        countstr = str(len(colDict.keys()))
        countstr += "*" if countstr != "0" else "\N{Check Mark}"
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.collideTab),
            f"&Colliding Pages ({countstr})",
        )

    def viewCPage(self):
        pvi = self.ui.collideTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.collideModel.item(r, 0).text()
        test = int(self.collideModel.item(r, 3).text())
        page = int(self.collideModel.item(r, 4).text())
        version = int(self.collideModel.item(r, 5).text())

        vop = self.msgr.getTPageImage(test, page, version)
        vcp = self.msgr.getCollidingImage(fname)
        if vop is None or vcp is None:
            return
        # Context manager not appropriate, Issue #1996
        f_orig = Path(tempfile.NamedTemporaryFile(delete=False).name)
        f_collides = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f_orig, "wb") as fh:
            fh.write(vop)
        with open(f_collides, "wb") as fh:
            fh.write(vcp)
        cvw = CollideViewWindow(self, f_orig, f_collides, test, page)
        if cvw.exec_() == QDialog.Accepted:
            if cvw.action == "original":
                pm = QPixmap()
                pm.loadFromData(
                    resources.read_binary(plom.client.icons, "manager_discard.svg")
                )
                self.collideModel.item(r, 1).setIcon(QIcon(pm))
                self.collideModel.item(r, 2).setText("discard")
            elif cvw.action == "collide":
                pm = QPixmap()
                pm.loadFromData(
                    resources.read_binary(plom.client.icons, "manager_test.svg")
                )
                self.collideModel.item(r, 1).setIcon(QIcon(pm))
                self.collideModel.item(r, 2).setText("replace")
        f_orig.unlink()
        f_collides.unlink()

    def doCActions(self):
        for r in range(self.collideModel.rowCount()):
            if self.collideModel.item(r, 2).text() == "discard":
                self.msgr.removeCollidingImage(self.collideModel.item(r, 0).text())
            elif self.collideModel.item(r, 2).text() == "replace":
                try:
                    self.msgr.collidingToTestPage(
                        self.collideModel.item(r, 0).text(),
                        self.collideModel.item(r, 3).text(),
                        self.collideModel.item(r, 4).text(),
                        self.collideModel.item(r, 5).text(),
                    )
                except (PlomOwnersLoggedInException, PlomConflict) as err:

                    ErrorMessage(f"{err}").exec_()
            else:
                pass
                # print(
                #     "No action for file {}.".format(self.collideModel.item(r, 0).text())
                # )
        self.refreshCList()

    def initDiscardTab(self):
        self.discardModel = QStandardItemModel(0, 4)
        self.ui.discardTV.setModel(self.discardModel)
        self.ui.discardTV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.discardTV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.discardModel.setHorizontalHeaderLabels(
            [
                "FullFile",
                "File",
                "Reason discarded",
                "Action to be taken",
            ]
        )
        self.ui.discardTV.setIconSize(QSize(96, 96))
        self.ui.discardTV.activated.connect(self.viewDPage)
        self.ui.discardTV.setColumnHidden(0, True)
        self.refreshDList()

    def refreshDList(self):
        self.discardModel.removeRows(0, self.discardModel.rowCount())
        # list of pairs [filename, reason]
        disList = self.msgr.getDiscardNames()
        r = 0
        for fname, reason in disList:
            it0 = QStandardItem(fname)
            it1 = QStandardItem(os.path.split(fname)[1])
            pm = QPixmap()
            pm.loadFromData(
                resources.read_binary(plom.client.icons, "manager_none.svg")
            )
            it1.setIcon(QIcon(pm))
            it2 = QStandardItem(reason)
            it3 = QStandardItem("none")
            it3.setTextAlignment(Qt.AlignCenter)
            self.discardModel.insertRow(r, [it0, it1, it2, it3])
            r += 1
        self.ui.discardTV.resizeRowsToContents()
        self.ui.discardTV.resizeColumnsToContents()
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.discardTab),
            "&Discarded Pages ({})".format(len(disList)),
        )

    def viewDPage(self):
        pvi = self.ui.discardTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        fname = self.discardModel.item(r, 0).text()
        vdp = self.msgr.getDiscardImage(fname)
        if vdp is None:
            return
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(vdp)
        dvw = DiscardViewWindow(self, f)
        if True:  # temp minimise diff
            if dvw.exec_() == QDialog.Accepted:
                if dvw.action == "unknown":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_move.svg")
                    )
                    self.discardModel.item(r, 1).setIcon(QIcon(pm))
                    self.discardModel.item(r, 3).setText("move")
                elif dvw.action == "none":
                    pm = QPixmap()
                    pm.loadFromData(
                        resources.read_binary(plom.client.icons, "manager_none.svg")
                    )
                    self.discardModel.item(r, 1).setIcon(QIcon(pm))
                    self.discardModel.item(r, 3).setText("none")
        f.unlink()

    def doDActions(self):
        for r in range(self.discardModel.rowCount()):
            if self.discardModel.item(r, 3).text() == "move":
                self.msgr.discardToUnknown(self.discardModel.item(r, 0).text())
            else:
                pass
                # print(
                #     "No action for file {}.".format(self.discardModel.item(r, 0).text())
                # )
        self.refreshDList()
        self.refreshUList()

    def initDanglingTab(self):
        self.danglingModel = QStandardItemModel(0, 5)
        self.ui.danglingTV.setModel(self.danglingModel)
        self.ui.danglingTV.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.danglingTV.setSelectionMode(QAbstractItemView.SingleSelection)
        self.danglingModel.setHorizontalHeaderLabels(
            ["Type", "Test", "Group", "Code", "Page / Order"]
        )
        self.ui.danglingTV.activated.connect(self.viewDanglingPage)
        self.refreshDangList()

    def refreshDangList(self):
        self.danglingModel.removeRows(0, self.danglingModel.rowCount())
        # list of dicts
        dangList = self.msgr.RgetDanglingPages()
        r = 0
        for dang in dangList:
            it0 = QStandardItem(f"{dang['type']}")
            it1 = QStandardItem(f"{dang['test']}")
            it2 = QStandardItem(f"{dang['group']}")
            it3 = QStandardItem(f"{dang['code']}")
            if dang["type"] == "tpage":
                it4 = QStandardItem(f"{dang['page']}")
            else:
                it4 = QStandardItem(f"{dang['order']}")
            self.danglingModel.insertRow(r, [it0, it1, it2, it3, it4])
            r += 1
        self.ui.danglingTV.resizeRowsToContents()
        self.ui.danglingTV.resizeColumnsToContents()

        countstr = str(len(dangList))
        countstr += "*" if countstr != "0" else "\N{Check Mark}"
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.dangleTab),
            f"Dan&gling Pages ({countstr})",
        )

    def viewDanglingPage(self):
        pvi = self.ui.danglingTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        test_number = int(self.danglingModel.item(r, 1).text())
        self.viewWholeTest(test_number)

    def removeDanglingPage(self):
        pvi = self.ui.danglingTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        # recreate the page name
        test_number = int(self.danglingModel.item(r, 1).text())
        page_name = self.danglingModel.item(r, 3).text()
        msg = WarningQuestion(
            self,
            f"Will remove the selected page {page_name} from the selected test {test_number}.",
            "Are you sure you wish to do this? (not reversible)",
        )
        if msg.exec_() == QMessageBox.No:
            return
        try:
            rval = self.msgr.removeSinglePage(test_number, page_name)
            ErrorMessage("{}".format(rval)).exec_()
        except PlomOwnersLoggedInException as err:
            ErrorMessage(
                "Cannot remove scanned pages from that test - owners of tasks in that test are logged in: {}".format(
                    err.args[-1]
                )
            ).exec_()

    # ###################
    # Progress tab stuff
    def initProgressTab(self):
        self.initOverallTab()
        self.initMarkTab()
        self.initIDTab()
        self.initOutTab()

    def refreshProgressTab(self):
        self.refreshOverallTab()
        self.refreshMarkTab()
        self.refreshIDTab()
        self.refreshOutTab()

    def initOverallTab(self):
        self.ui.overallTW.setHorizontalHeaderLabels(
            ["Test number", "Scanned", "Identified", "Questions Marked"]
        )
        self.ui.overallTW.activated.connect(self.viewTestStatus)
        self.ui.overallTW.setSortingEnabled(True)
        self.refreshOverallTab()

    def viewTestStatus(self):
        pvi = self.ui.overallTW.selectedItems()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        testNumber = int(self.ui.overallTW.item(r, 0).text())
        stats = self.msgr.RgetStatus(testNumber)
        TestStatus(self.numberOfQuestions, stats).exec_()

    def refreshOverallTab(self):
        self.ui.overallTW.clearContents()
        self.ui.overallTW.setRowCount(0)

        opDict = self.msgr.RgetCompletionStatus()
        tk = list(opDict.keys())
        tk.sort(key=int)  # sort in numeric order
        # each dict value is [Scanned, Identified, #Marked]
        r = 0
        for t in tk:
            self.ui.overallTW.insertRow(r)
            self.ui.overallTW.setItem(r, 0, QTableWidgetItem(str(t).rjust(4)))

            it = QTableWidgetItem("{}".format(opDict[t][0]))
            if opDict[t][0]:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been scanned")
            elif opDict[t][2] > 0:
                it.setBackground(QBrush(Qt.red))
                it.setToolTip("Has been (part-)marked but not completely scanned.")

            self.ui.overallTW.setItem(r, 1, it)

            it = QTableWidgetItem("{}".format(opDict[t][1]))
            if opDict[t][1]:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been identified")
            self.ui.overallTW.setItem(r, 2, it)

            it = QTableWidgetItem(str(opDict[t][2]).rjust(3))
            if opDict[t][2] == self.numberOfQuestions:
                it.setBackground(QBrush(Qt.green))
                it.setToolTip("Has been marked")
            self.ui.overallTW.setItem(r, 3, it)
            r += 1

    def initIDTab(self):
        self.refreshIDTab()
        self.ui.idPB.setFormat("%v / %m")
        self.ui.predictionTW.setColumnCount(3)
        self.ui.predictionTW.setHorizontalHeaderLabels(["Test", "Student ID", "Name"])
        self.ui.predictionTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.predictionTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.predictionTW.setAlternatingRowColors(True)
        self.ui.predictionTW.activated.connect(self.viewIDPage)

    def refreshIDTab(self):
        ti = self.msgr.IDprogressCount()
        self.ui.papersLE.setText(str(ti[1]))
        self.ui.idPB.setValue(ti[0])
        self.ui.idPB.setMaximum(ti[1])
        self.getPredictions()

    def selectRectangle(self):
        try:
            imageList = self.msgr.IDgetImageFromATest()
        except PlomNoMoreException as err:
            ErrorMessage(f"No unIDd images to show - {err}").exec_()
            return
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i, img_bytes in enumerate(imageList):
                img_ext = imghdr.what(None, h=img_bytes)
                tmp = Path(td) / "id.{}.{}".format(i, img_ext)
                with open(tmp, "wb") as fh:
                    fh.write(img_bytes)
                inames.append(tmp)
            srw = SelectRectangleWindow(self, inames)
            if srw.exec_() == QDialog.Accepted:
                self.IDrectangle = srw.rectangle
                self.IDwhichFile = srw.whichFile
                if (
                    self.IDrectangle is None
                ):  # We do not allow the IDReader to run if no rectangle is selected (this would cause a crash)
                    self.ui.predictButton.setEnabled(False)
                else:
                    self.ui.predictButton.setEnabled(True)

    def viewIDPage(self):
        idi = self.ui.predictionTW.selectedIndexes()
        if len(idi) == 0:
            return
        test = int(self.ui.predictionTW.item(idi[0].row(), 0).text())
        sid = int(self.ui.predictionTW.item(idi[0].row(), 1).text())
        try:
            img_bytes = self.msgr.request_ID_image(test)
        except PlomException as err:
            ErrorMessage(err).exec_()
            return

        if not img_bytes:
            return
        with tempfile.TemporaryDirectory() as td:
            img_ext = imghdr.what(None, h=img_bytes)
            imageName = Path(td) / f"id.{img_ext}"
            with open(imageName, "wb") as fh:
                fh.write(img_bytes)
            IDViewWindow(self, imageName, sid).exec_()

    def runPredictor(self, ignoreStamp=False):
        rmsg = self.msgr.IDrunPredictions(
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
            sm = SimpleQuestion(
                self,
                f"IDReader was last run at {rmsg[1]}",
                "Do you want to rerun it?",
            )
            if sm.exec_() == QMessageBox.No:
                return
            self.runPredictor(ignoreStamp=True)

    def un_id_paper(self):
        # should we populate "test" from the list view?
        # idi = self.ui.predictionTW.selectedIndexes()
        # if idi:
        #     test = int(self.ui.predictionTW.item(idi[0].row(), 0).text())
        #     sid = int(self.ui.predictionTW.item(idi[0].row(), 1).text())

        test, ok = QInputDialog.getText(self, "Unidentify a paper", "Un-ID which paper")
        if not ok or not test:
            return
        iDict = self.msgr.getIdentified()
        msg = f"Do you want to reset the ID of test number {test}?"
        if test in iDict:
            sid, sname = iDict[test]
            msg += f"\n\nCurrently is {sid}: {sname}"
        else:
            msg += "\n\nCan't find current ID - is likely not ID'd yet."
        if SimpleQuestion(self, msg).exec_() == QMessageBox.No:
            return
        # self.msgr.id_paper(test, "", "")
        self.msgr.un_id_paper(test)

    def getPredictions(self):
        csvfile = self.msgr.IDrequestPredictions()
        pdict = {}
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        for row in reader:
            pdict[int(row["test"])] = str(row["id"])
        iDict = self.msgr.getIdentified()
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
        msg = SimpleQuestion(
            self,
            "Are you sure you want the server to delete predicted IDs?"
            " (note that this does not delete user-inputted IDs)",
        )
        if msg.exec_() == QMessageBox.No:
            return
        # returns [True] or [False, message]
        rval = self.msgr.IDdeletePredictions()
        if rval[0] is False:  # some sort of problem, show returned message
            ErrorMessage(rval[1]).exec_()
        else:
            self.getPredictions()

    def initMarkTab(self):
        grid = QGridLayout()
        self.pd = {}
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = self.msgr.getProgress(q, v)
                self.pd[(q, v)] = ProgressBox(self, q, v, stats)
                grid.addWidget(self.pd[(q, v)], q, v)
        self.ui.markBucket.setLayout(grid)

    def refreshMarkTab(self):
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = self.msgr.getProgress(q, v)
                self.pd[(q, v)].refresh(stats)

    def viewMarkHistogram(self, question, version):
        mhist = self.msgr.getMarkHistogram(question, version)
        QVHistogram(question, version, mhist).exec_()

    def initOutTab(self):
        self.ui.tasksOutTW.setColumnCount(3)
        self.ui.tasksOutTW.setHorizontalHeaderLabels(["Task", "User", "Time"])

    def refreshOutTab(self):
        tasksOut = self.msgr.RgetOutToDo()
        self.ui.tasksOutTW.clearContents()
        self.ui.tasksOutTW.setRowCount(0)

        if len(tasksOut) == 0:
            self.ui.tasksOutTW.setEnabled(False)
            return

        self.ui.tasksOutTW.setEnabled(True)
        r = 0
        for x in tasksOut:
            self.ui.tasksOutTW.insertRow(r)
            self.ui.tasksOutTW.setItem(r, 0, QTableWidgetItem(str(x[0])))
            self.ui.tasksOutTW.setItem(r, 1, QTableWidgetItem(str(x[1])))
            self.ui.tasksOutTW.setItem(r, 2, QTableWidgetItem(str(x[2])))
            r += 1

    def todo(self, msg=""):
        ErrorMessage("This is on our to-do list" + msg).exec_()

    ##################
    # review tab stuff

    def initReviewTab(self):
        self.initRevMTab()
        self.initRevIDTab()

    def refreshRev(self):
        self.refreshIDRev()
        self.refreshMRev()

    def initRevMTab(self):
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
        ulist = self.msgr.getUserList()
        self.ui.userCB.addItem("*")
        for u in ulist:
            self.ui.userCB.addItem(u)
        self.ui.filterB.clicked.connect(self.filterReview)

    def refreshMRev(self):
        """Refresh the user list in the marking review tab."""
        # clean out the combox box and then rebuild it.
        self.ui.userCB.clear()
        ulist = self.msgr.getUserList()
        self.ui.userCB.addItem("*")
        for u in ulist:
            self.ui.userCB.addItem(u)

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
        markedOnly = True if self.ui.markedOnlyCB.checkState() == Qt.Checked else False
        mrList = self.msgr.getMarkReview(
            self.ui.questionCB.currentText(),
            self.ui.versionCB.currentText(),
            self.ui.userCB.currentText(),
            markedOnly,
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
            if dat[3] == "n/a":
                for k in range(7):
                    self.ui.reviewTW.item(r, k).setBackground(QBrush(Qt.yellow))
            r += 1

    def reviewAnnotated(self):
        rvi = self.ui.reviewTW.selectedIndexes()
        if len(rvi) == 0:
            return
        r = rvi[0].row()
        # no action if row is unmarked
        # text in item is rjust(4)'d - so <space>n/a is the string
        if self.ui.reviewTW.item(r, 3).text() == " n/a":
            # TODO - in future fire up reviewer with original pages
            return
        test = int(self.ui.reviewTW.item(r, 0).text())
        question = int(self.ui.reviewTW.item(r, 1).text())
        version = int(self.ui.reviewTW.item(r, 2).text())
        img = self.msgr.get_annotations_image(test, question)
        # TODO: issue #1909: use .png/.jpg: inspect bytes with imghdr?
        # TODO: but more likely superseded by "pagedata" changes
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(img)
        rvw = ReviewViewWindow(self, [f])
        if rvw.exec() == QDialog.Accepted:
            if rvw.action == "review":
                # first remove auth from that user - safer.
                if self.ui.reviewTW.item(r, 4).text() != "reviewer":
                    self.msgr.clearAuthorisationUser(self.ui.reviewTW.item(r, 4).text())
                # then map that question's owner "reviewer"
                self.msgr.MreviewQuestion(test, question, version)
                self.ui.reviewTW.item(r, 4).setText("reviewer")
        f.unlink()

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
        irList = self.msgr.getIDReview()
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
                SimpleQuestion(
                    self,
                    "This paper was ID'd automatically, are you sure you wish to review it?",
                ).exec_()
                != QMessageBox.Yes
            ):
                return

        test = int(self.ui.reviewIDTW.item(r, 0).text())
        img_bytes = self.msgr.request_ID_image(test)
        with tempfile.TemporaryDirectory() as td:
            img_ext = imghdr.what(None, h=img_bytes)
            imageName = Path(td) / f"id.0.{img_ext}"
            with open(imageName, "wb") as fh:
                fh.write(img_bytes)
            rvw = ReviewViewWindow(self, imageName, "ID pages")
            if rvw.exec() == QDialog.Accepted:
                if rvw.action == "review":
                    # first remove auth from that user - safer.
                    if self.ui.reviewIDTW.item(r, 1).text() != "reviewer":
                        self.msgr.clearAuthorisationUser(
                            self.ui.reviewIDTW.item(r, 1).text()
                        )
                    # then map that question's owner "reviewer"
                    self.ui.reviewIDTW.item(r, 1).setText("reviewer")
                    self.msgr.IDreviewID(test)

    ##################
    # Solution tab stuff
    def initSolutionTab(self):
        self.tempDirectory = tempfile.TemporaryDirectory(prefix="plom_manager_")
        self.solnPath = self.tempDirectory.name
        # set up the viewer
        self.solnIV = ImageViewWidget(self)
        self.ui.solnGBLayout.addWidget(self.solnIV)

        self.ui.solnQSB.setMaximum(self.numberOfQuestions)
        self.ui.solnQSB.valueChanged.connect(self.viewCurrentSolution)
        self.ui.solnVSB.setMaximum(self.numberOfVersions)
        self.ui.solnVSB.valueChanged.connect(self.viewCurrentSolution)

        self.ui.solnDeleteB.clicked.connect(self.deleteCurrentSolution)
        self.ui.solnViewB.clicked.connect(self.viewCurrentSolution)
        self.ui.solnRefreshB.clicked.connect(self.refreshCurrentSolution)
        self.ui.solnUploadB.clicked.connect(self.uploadSolution)

    def refreshCurrentSolution(self):
        try:
            imgBytes = self.msgr.getSolutionImage(
                self.ui.solnQSB.value(), self.ui.solnVSB.value()
            )
        except PlomNoSolutionException:
            self.solnIV.updateImage([])
            return False
        # save the image
        solutionName = os.path.join(
            self.solnPath,
            "solution.{}.{}.png".format(
                self.ui.solnQSB.value(), self.ui.solnVSB.value()
            ),
        )
        with open(solutionName, "wb") as fh:
            fh.write(imgBytes)
        self.solnIV.updateImage(solutionName)
        return True

    def viewCurrentSolution(self):
        solutionName = os.path.join(
            self.solnPath,
            "solution.{}.{}.png".format(
                self.ui.solnQSB.value(), self.ui.solnVSB.value()
            ),
        )
        # check if file there already
        if os.path.isfile(solutionName):
            self.solnIV.updateImage(solutionName)
        else:  # not there - so try to update it
            self.refreshCurrentSolution()

    def uploadSolution(self):
        # currently only png
        fname = QFileDialog.getOpenFileName(
            self, "Get solution image", "./", "PNG files (*.png)"
        )  # returns (name, type)
        if fname[0] == "":  # user didn't select file
            return
        # check file is actually there
        if not os.path.isfile(fname[0]):
            return
        # push file to server
        self.msgr.putSolutionImage(
            self.ui.solnQSB.value(), self.ui.solnVSB.value(), fname[0]
        )
        self.refreshCurrentSolution()

    def deleteCurrentSolution(self):
        if (
            SimpleQuestion(
                self,
                f"Are you sure that you want to delete solution to"
                f" question {self.ui.solnQSB.value()}"
                f" version {self.ui.solnVSB.value()}.",
            ).exec_()
            == QMessageBox.Yes
        ):
            self.msgr.deleteSolutionImage(
                self.ui.solnQSB.value(), self.ui.solnVSB.value()
            )
            solutionName = os.path.join(
                self.solnPath,
                "solution.{}.{}.png".format(
                    self.ui.solnQSB.value(), self.ui.solnVSB.value()
                ),
            )
            os.unlink(solutionName)
            self.solnIV.updateImage([])
        else:
            return

    ##################
    # User tab stuff

    def initUserTab(self):
        self.initUserListTab()
        self.initProgressQUTabs()

    def initUserListTab(self):
        self.ui.userListTW.setColumnCount(7)
        self.ui.userListTW.setHorizontalHeaderLabels(
            [
                "Username",
                "Enabled",
                "Logged in",
                "Last activity",
                "Last action",
                "Papers IDd",
                "Questions Marked",
            ]
        )
        self.ui.userListTW.setSortingEnabled(True)
        self.ui.userListTW.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.userListTW.setSelectionBehavior(QAbstractItemView.SelectRows)

    def initProgressQUTabs(self):
        self.ui.QPUserTW.setColumnCount(5)
        self.ui.QPUserTW.setHeaderLabels(
            [
                "Question",
                "Version",
                "User",
                "Number Marked",
                "Avg time per task",
                "Percentage of Q/V marked",
            ]
        )
        # self.ui.QPUserTW.setSortingEnabled(True)
        self.ui.QPUserTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.QPUserTW.setSelectionBehavior(QAbstractItemView.SelectRows)
        # and the other tab
        self.ui.PUQTW.setColumnCount(5)
        self.ui.PUQTW.setHeaderLabels(
            [
                "User",
                "Question",
                "Version",
                "Number Marked",
                "Avg time per task",
                "Percentage of Q/V marked",
            ]
        )
        # self.ui.PUQTW.setSortingEnabled(True)
        self.ui.PUQTW.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.PUQTW.setSelectionBehavior(QAbstractItemView.SelectRows)

    def forceLogout(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return

        selectedUsers = [self.ui.userListTW.item(i.row(), 0).text() for i in ri[::7]]

        if "manager" in selectedUsers:
            ErrorMessage(
                "You cannot force-logout the manager. To logout, click on the Quit button."
            ).exec_()
            return
        if (
            SimpleQuestion(
                self,
                "Are you sure you want to force-logout users {}?".format(selectedUsers)
                # do something about this formatting, right now it's just a python list
            ).exec_()
            == QMessageBox.Yes
        ):
            for user in selectedUsers:
                self.msgr.clearAuthorisationUser(user)
            self.refreshUserList()

    def enableUsers(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return

        selectedUsers = [self.ui.userListTW.item(i.row(), 0).text() for i in ri[::7]]

        for user in selectedUsers:
            try:
                self.msgr.enableUser(user)
            except PlomConflict as e:
                WarnMsg(self, str(e)).exec_()
        self.refreshUserList()

    def disableUsers(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return

        selectedUsers = [self.ui.userListTW.item(i.row(), 0).text() for i in ri[::7]]

        msg = "Are you sure you want to disable "
        msg += "users " if len(selectedUsers) > 1 else "user "
        msg += ", ".join(f'"{x}"' for x in selectedUsers)
        if SimpleQuestion(self, msg).exec_() != QMessageBox.Yes:
            return
        for user in selectedUsers:
            try:
                self.msgr.disableUser(user)
            except PlomConflict as e:
                WarnMsg(self, str(e)).exec_()
        self.refreshUserList()

    def changeUserPassword(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return
        if len(ri) > 7:
            ErrorMessage(
                "You can only change the password of one user at a time."
            ).exec()
            return

        r = ri[0].row()
        user = self.ui.userListTW.item(r, 0).text()
        cpwd = UserDialog(name=user)
        if cpwd.exec_() == QDialog.Accepted:
            rval = self.msgr.createModifyUser(user, cpwd.password)
            ErrorMessage(rval[1]).exec_()
        return

    def createUser(self):
        # need to pass list of existing users
        uList = [
            self.ui.userListTW.item(r, 0).text()
            for r in range(self.ui.userListTW.rowCount())
        ]
        cpwd = UserDialog(name=None, extant=uList)
        if cpwd.exec_() == QDialog.Accepted:
            rval = self.msgr.createModifyUser(cpwd.name, cpwd.password)
            ErrorMessage(rval[1]).exec_()
            self.refreshUserList()
        return

    def refreshUserList(self):
        uDict = self.msgr.getUserDetails()
        self.ui.userListTW.clearContents()
        self.ui.userListTW.setRowCount(0)
        r = 0
        for u in uDict:
            dat = uDict[u]
            self.ui.userListTW.insertRow(r)

            # change the last activity to be human readable
            rawTimestamp = dat[2]

            time = arrow.get(rawTimestamp, "YY:MM:DD-HH:mm:ss")
            dat[2] = time.humanize()

            # rjust(4) entries so that they can sort like integers... without actually being integers
            self.ui.userListTW.setItem(r, 0, QTableWidgetItem("{}".format(u)))
            for k in range(6):
                self.ui.userListTW.setItem(
                    r, k + 1, QTableWidgetItem("{}".format(dat[k]))
                )
            if dat[0]:
                self.ui.userListTW.item(r, 1).setBackground(QBrush(Qt.green))
            else:
                self.ui.userListTW.item(r, 1).setBackground(QBrush(Qt.red))
            if dat[1]:
                self.ui.userListTW.item(r, 2).setBackground(QBrush(Qt.green))

            if u in ["manager", "scanner", "reviewer"]:
                self.ui.userListTW.item(r, 0).setBackground(QBrush(Qt.green))

            # add tooltip to show timestamp when hovering over human readable description
            self.ui.userListTW.item(r, 3).setToolTip(rawTimestamp)

            r += 1

    def refreshProgressQU(self):
        # delete the children of each toplevel items
        # for TW 1
        root = self.ui.QPUserTW.invisibleRootItem()
        for l0 in range(self.ui.QPUserTW.topLevelItemCount()):
            l0i = self.ui.QPUserTW.topLevelItem(0)
            for l1 in range(self.ui.QPUserTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)
        # for TW 2
        root = self.ui.PUQTW.invisibleRootItem()
        for l0 in range(self.ui.PUQTW.topLevelItemCount()):
            l0i = self.ui.PUQTW.topLevelItem(0)
            for l1 in range(self.ui.PUQTW.topLevelItem(0).childCount()):
                l0i.removeChild(l0i.child(0))
            root.removeChild(l0i)
        # for TW1 and TW2
        # get list of everything done by users, store by user for TW2
        # use directly for TW1
        uprog = defaultdict(list)
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                qpu = self.msgr.getQuestionUserProgress(q, v)
                l0 = QTreeWidgetItem([str(q).rjust(4), str(v).rjust(2)])
                for (u, n, t) in qpu[1:]:
                    # question, version, no marked, avg time
                    uprog[u].append([q, v, n, t, qpu[0]])
                    pb = QProgressBar()
                    pb.setMaximum(qpu[0])
                    pb.setValue(n)
                    l1 = QTreeWidgetItem(["", "", str(u), str(n).rjust(4), f"{t}s"])
                    l0.addChild(l1)
                    self.ui.QPUserTW.setItemWidget(l1, 5, pb)
                self.ui.QPUserTW.addTopLevelItem(l0)
        # for TW2
        for u in uprog:
            l0 = QTreeWidgetItem([str(u)])
            for qvn in uprog[u]:  # will be in q,v,n,t, ntot in qv order
                pb = QProgressBar()
                pb.setMaximum(qvn[4])
                pb.setValue(qvn[2])
                l1 = QTreeWidgetItem(
                    [
                        "",
                        str(qvn[0]).rjust(4),
                        str(qvn[1]).rjust(2),
                        str(qvn[2]).rjust(4),
                        f"{qvn[3]}s",
                    ]
                )
                l0.addChild(l1)
                self.ui.PUQTW.setItemWidget(l1, 5, pb)
            self.ui.PUQTW.addTopLevelItem(l0)
