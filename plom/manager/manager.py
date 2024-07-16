# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2021-2022 Elizabeth Xiao
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Natalie Balashov

from collections import defaultdict
import html
import logging
import os
from pathlib import Path
import sys
import tempfile
from time import time

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

import arrow

from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
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

import plom.client.ui_files
import plom.client.icons

from plom.client.useful_classes import ErrorMsg, InfoMsg, WarnMsg
from plom.client.useful_classes import SimpleQuestion, WarningQuestion
from plom.client.tagging import AddRemoveTagDialog
from plom.client.viewers import WholeTestView, GroupView
from plom.client.downloader import Downloader
from plom.client.about_dialog import show_about_dialog
from plom.client import ImageViewWidget

from .unknownpageview import UnknownViewWindow
from .collideview import CollideViewWindow
from .discardview import DiscardViewWindow
from .reviewview import ReviewViewWindow, ReviewViewWindowID
from .reviewview import review_beta_warning, revert_beta_warning
from .selectrectangle import SelectRectangleWindow
from plom.plom_exceptions import (
    PlomAPIException,
    PlomAuthenticationException,
    PlomBadTagError,
    PlomBenignException,
    PlomConflict,
    PlomExistingDatabase,
    PlomExistingLoginException,
    # PlomOwnersLoggedInException,
    PlomRangeException,
    PlomServerNotReady,
    PlomTakenException,
    PlomUnidentifiedPaperException,
    PlomNoMoreException,
    PlomNoPaper,
    PlomNoSolutionException,
)
from plom.messenger import ManagerMessenger
from plom.aliceBob import simple_password
from plom.misc_utils import arrowtime_to_simple_string
from plom.specVerifier import get_question_label
from plom.misc_utils import format_int_list_with_runs

from plom import __version__, Plom_Legacy_Server_API_Version
from plom import Default_Port


log = logging.getLogger("manager")


class UserDialog(QDialog):
    """Simple dialog to enter username and password."""

    def __init__(self, parent, title, *, name=None):
        super().__init__(parent)
        self.name = name

        self.setWindowTitle(title)
        self.userL = QLabel("Username:")
        self.pwL = QLabel("Password:")
        self.pwL2 = QLabel("and again:")
        self.userLE = QLineEdit(self.name)
        if name is not None:
            self.userLE.setEnabled(False)
        initialpw = simple_password()
        self.pwLE = QLineEdit(initialpw)
        # self.pwLE.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwLE2 = QLineEdit(initialpw)
        # self.pwLE2.setEchoMode(QLineEdit.EchoMode.Password)
        self.okB = QPushButton("Accept")
        self.okB.clicked.connect(self.validate)
        self.cnB = QPushButton("Cancel")
        self.cnB.clicked.connect(self.reject)

        self.pwCB = QCheckBox("(hide/show)")
        self.pwCB.setChecked(False)
        self.pwCB.stateChanged.connect(self.togglePWShow)
        self.pwNewB = QPushButton("New rand pwd")
        self.pwNewB.clicked.connect(self.newRandomPassword)

        grid = QGridLayout()
        grid.addWidget(self.userL, 1, 1)
        grid.addWidget(self.userLE, 1, 2)
        grid.addWidget(self.pwL, 2, 1)
        grid.addWidget(self.pwLE, 2, 2)
        grid.addWidget(self.pwCB, 2, 3)
        grid.addWidget(self.pwL2, 3, 1)
        grid.addWidget(self.pwLE2, 3, 2)
        grid.addWidget(self.pwNewB, 3, 3)
        grid.addWidget(self.okB, 4, 3)
        grid.addWidget(self.cnB, 4, 1)

        self.setLayout(grid)

    def togglePWShow(self):
        if self.pwCB.isChecked():
            self.pwLE.setEchoMode(QLineEdit.EchoMode.Password)
            self.pwLE2.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.pwLE.setEchoMode(QLineEdit.EchoMode.Normal)
            self.pwLE2.setEchoMode(QLineEdit.EchoMode.Normal)

    def newRandomPassword(self):
        newpw = simple_password()
        self.pwLE.setText(newpw)
        self.pwLE2.setText(newpw)

    def validate(self):
        """Check username not in list and that passwords match."""
        if self.pwLE.text() != self.pwLE2.text():
            WarnMsg(self, "Passwords do not match").exec()
            return
        self.name = self.userLE.text()
        self.password = self.pwLE.text()
        self.accept()


class QVHistogram(QDialog):
    """A non-modal dialog showing histograms.

    A note on modality: because this is parented to Manager (see super
    init call) but non-modal you can open as many as you want.  At
    least in the Gnome environment, the window manager keeps them all
    on top of Manager (but allows the focus to switch back to Manager).
    Compare to `SolutionViewer` which is unparented so not on top.
    """

    def __init__(self, parent, qlabel, qidx, v, hist):
        super().__init__(parent)
        self.setWindowTitle(f"{qlabel} version {v} histograms")
        tot = 0
        mx = 0
        dist = {}
        for u in hist:
            for m in hist[u]:
                im = int(m)
                s = int(hist[u][m])
                mx = max(mx, im)
                tot += s
                if im not in dist:
                    dist[im] = 0
                dist[im] += s

        grid = QGridLayout()

        eG = QGroupBox("All markers")
        gg = QVBoxLayout()
        gg.addWidget(QLabel("Number of papers: {}".format(tot)))
        gp = QHBoxLayout()
        for im in range(0, mx + 1):
            pb = QProgressBar()
            pb.setOrientation(Qt.Orientation.Vertical)
            if im not in dist:
                pb.setValue(0)
            else:
                pb.setValue((100 * dist[im]) // tot)
            pb.setToolTip("{} = {}%".format(im, pb.value()))
            gp.addWidget(pb)
        gg.addLayout(gp)
        eG.setLayout(gg)
        grid.addWidget(eG, 0, 0)

        max_number_of_rows = 4  # should depend on user's viewport
        current_row = 1
        current_column = 0

        uG = {}
        for u in hist:
            utot = 0
            for m in hist[u]:
                utot += hist[u][m]
            uG[u] = QGroupBox("Marker: {}".format(u))
            gg = QVBoxLayout()
            gg.addWidget(QLabel("Number of papers: {}".format(utot)))
            gp = QHBoxLayout()
            for im in range(0, mx + 1):
                m = str(im)
                pb = QProgressBar()
                pb.setOrientation(Qt.Orientation.Vertical)
                if m not in hist[u]:
                    pb.setValue(0)
                else:
                    pb.setValue((100 * hist[u][m]) // utot)
                pb.setToolTip("{} = {}%".format(m, pb.value()))
                gp.addWidget(pb)
            gg.addLayout(gp)
            uG[u].setLayout(gg)
            grid.addWidget(uG[u], current_row, current_column)
            current_row = (current_row + 1) % max_number_of_rows
            if current_row == 0:
                current_column = current_column + 1

        cB = QPushButton("&Close")
        cB.clicked.connect(self.accept)
        grid.addWidget(cB)
        self.setLayout(grid)
        self.show()


class TestStatus(QDialog):
    def __init__(self, parent, qlabels, status):
        super().__init__(parent)
        self.setWindowTitle(f'Status of Paper {status["number"]:04}')

        idCB = QCheckBox("Identified")
        idCB.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        idCB.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if status["identified"]:
            idCB.setChecked(True)
        mkCB = QCheckBox("Fully marked")
        mkCB.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        mkCB.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if status["marked"]:
            mkCB.setChecked(True)

        hb = QHBoxLayout()
        vb1 = QVBoxLayout()
        vb2 = QVBoxLayout()
        hb.addLayout(vb1)
        hb.addLayout(vb2)
        vb1.addWidget(idCB)
        vb2.addWidget(mkCB)

        if status["identified"]:
            G = QGroupBox("Identification")
            gg = QVBoxLayout()
            gg.addWidget(QLabel("ID: {}".format(status["sid"])))
            gg.addWidget(QLabel("Name: {}".format(status["sname"])))
            gg.addWidget(QLabel("Who ID'd: {}".format(status["iwho"])))
            G.setLayout(gg)
            vb1.addWidget(G)
        vb1.addStretch(1)

        for i, qlabel in enumerate(qlabels):
            sq = str(i + 1)
            G = QGroupBox(f'{qlabel} version {status[sq]["version"]}')
            gg = QVBoxLayout()
            if status[sq]["marked"]:
                gg.addWidget(QLabel("Mark: {}".format(status[sq]["mark"])))
                gg.addWidget(QLabel("Username: {}".format(status[sq]["who"])))
            else:
                gg.addWidget(QLabel("Unmarked"))
            G.setLayout(gg)
            vb2.addWidget(G)
        vb2.addStretch(2)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        vb2.addWidget(buttons)
        self.setLayout(hb)


class ProgressBox(QGroupBox):
    def __init__(self, manager, qlabel, qidx, version):
        # This widget will be re-parented when its added to a layout
        super().__init__()
        self.setTitle(f"{qlabel} ver {version}")
        grid = QVBoxLayout()
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
        vhB = QPushButton("View histograms")
        vhB.clicked.connect(lambda: manager.viewMarkHistogram(qlabel, qidx, version))
        grid.addWidget(vhB)

        self.setLayout(grid)

    def refresh(self, stats):
        self.setEnabled(True)
        self.setVisible(True)
        self.pb.setMaximum(stats["NScanned"])
        self.pb.setValue(stats["NMarked"])

        if stats["NScanned"] == 0:
            self.setEnabled(False)
            self.setVisible(False)
            return
        if stats["NMarked"] > 0:
            self.avgL.setText(
                "Mean : Median : Mode = {:0.2f} : {} : {}".format(
                    stats["avgMark"], stats["medianMark"], stats["modeMark"]
                )
            )
            self.mmfL.setText(
                "Min : Max : Full = {} : {} : {}".format(
                    stats["minMark"], stats["maxMark"], stats["fullMark"]
                )
            )
            self.mtL.setText("Avg marking time = {:0.1f}s".format(stats["avgMTime"]))
            self.lhL.setText("{} marked in last hour".format(stats["NRecent"]))
        else:
            self.avgL.setText("Mean : Median : Mode  = N/A")
            self.mmfL.setText(
                "Min : Max : Full = N/A : N/A : {}".format(stats["fullMark"])
            )
            self.mtL.setText("Avg marking time = N/A")
            self.lhL.setText("None have been marked")


class Manager(QWidget):
    """Plom server management and marking progress UI tool."""

    def __init__(
        self, Qapp, *, server=None, user=None, password=None, manager_msgr=None
    ):
        """Start a new Plom Manager window.

        Args:
            Qapp (QApplication): the application for whom we are opening
                a window.

        Keyword Args:
            manager_msgr (ManagerMessenger/None): a connected ManagerMessenger.
                Note that the plain 'ol Messenger will not work.  By default
                or if `None` is passed, we'll make the user login or use
                other kwargs.
            server (str/None): what server.
            user (str/None): credientials.
            password (str/None): credientials.

        Returns:
            None
        """
        self.APIVersion = Plom_Legacy_Server_API_Version
        super().__init__()
        self.Qapp = Qapp
        self.msgr = manager_msgr
        print(
            "Plom Manager Client {} (communicates with legacy api {})".format(
                __version__, self.APIVersion
            )
        )
        uic.loadUi(resources.files(plom.client.ui_files) / "manager.ui", self)
        # TODO: temporary workaround
        self.ui = self

        self.setWindowTitle("{} {}".format(self.windowTitle(), __version__))
        if user:
            self.ui.userLE.setText(user)
        if password:
            self.ui.passwordLE.setText(password)
        if server:
            self.ui.serverLE.setText(server)
        self.ui.mportLabel2.setText(f"defaults to {Default_Port} if omitted")

        self.ui.passwordLE.setFocus()
        self.connectButtons()
        self.ui.configTab.setEnabled(False)
        self.ui.scanningAllTab.setEnabled(False)
        self.ui.progressAllTab.setEnabled(False)
        self.ui.solnTab.setEnabled(False)
        self.ui.reviewAllTab.setEnabled(False)
        self.ui.userAllTab.setEnabled(False)
        if self.msgr:
            server_ver_str = self.msgr.get_server_version()
            self.ui.infoLabel.setText(server_ver_str)
            self.initial_login()
            self._enable_downloader()
        else:
            if password:
                self.login()

    def _enable_downloader(self):
        self.downloader = getattr(self.Qapp, "downloader", None)
        # If Qapp doesn't have a Downloader, make a new one
        if self.downloader is None:
            tmpdir = tempfile.mkdtemp(prefix="plom_local_img_")
            self.downloader = Downloader(tmpdir, msgr=self.msgr)

    def connectButtons(self):
        self.ui.aboutButton.clicked.connect(lambda: show_about_dialog(self))
        self.ui.loginButton.clicked.connect(self.login)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.fontSB.valueChanged.connect(self.setFont)
        self.ui.scanRefreshB.clicked.connect(self.refreshScanTab)
        self.ui.progressRefreshB.clicked.connect(self.refreshProgressTab)
        self.ui.downloadCSVButton.clicked.connect(self.downloadCSV)
        self.ui.refreshIDPredictionsB.clicked.connect(self.getPredictions)
        self.ui.unidB.clicked.connect(self.un_id_paper)
        self.ui.unpredB.clicked.connect(self.remove_id_prediction)

        self.ui.configRefreshButton.clicked.connect(self.refreshConfig)
        self.ui.uploadSpecButton.clicked.connect(self.uploadSpec)
        self.ui.viewSpecButton.clicked.connect(self.viewSpec)
        self.ui.uploadClasslistButton.clicked.connect(self.uploadClasslist)
        self.ui.makeDatabaseButton.clicked.connect(self.makeDataBase)
        self.ui.makePapersFolderButton.clicked.connect(self.buildPapersChooseFolder)
        self.ui.makePapersButton.clicked.connect(self.buildPapers)

        self.ui.refreshReviewMarkingButton.clicked.connect(self.refreshMRev)
        self.ui.refreshReviewIDButton.clicked.connect(self.refreshIDRev)
        self.ui.refreshUserB.clicked.connect(self.refreshUserList)
        self.ui.refreshProgressQUB.clicked.connect(self.refreshProgressQU)
        self.ui.flagReviewButton.clicked.connect(self.reviewFlagTableRowsForReview)
        self.ui.removeAnnotationsButton.clicked.connect(self.removeAnnotationsFromRange)

        self.ui.rubricsDownloadButton.clicked.connect(self.rubricsDownload)
        self.ui.rubricsUploadButton.clicked.connect(self.rubricsUpload)
        self.ui.rubricsRefreshButton.clicked.connect(self.rubricsRefresh)

        self.ui.reassembleFolderButton.clicked.connect(self.reassembleChooseFolder)
        self.ui.reassembleButton.clicked.connect(self.reassemblePapers)
        self.ui.reassembleSolutionsButton.clicked.connect(self.reassembleSolutions)

        self.ui.removePagesB.clicked.connect(self.removePages)
        self.ui.subsPageB.clicked.connect(self.substitutePage)
        self.ui.forgiveAllDNMButton.clicked.connect(self.substituteAllDNMPages)
        self.ui.removePartScanB.clicked.connect(self.removePagesFromPartScan)
        self.ui.removeDanglingB.clicked.connect(self.removeDanglingPage)
        self.ui.refreshDanglingB.clicked.connect(self.refreshDangList)

        self.ui.actionUButton.clicked.connect(self.doUActions)
        self.ui.actionCButton.clicked.connect(self.doCActions)
        self.ui.discardToUnknownButton.clicked.connect(self.viewDiscardPage)
        self.ui.selectRectButton.clicked.connect(self.selectRectangle)
        self.ui.machineReadButton.clicked.connect(self.id_reader_run)
        self.ui.machineReadRefreshButton.clicked.connect(self.id_reader_get_log)
        self.ui.machineReadKillButton.clicked.connect(self.id_reader_kill)
        self.ui.predictButton.clicked.connect(self.run_predictor)
        self.ui.delPredButton.clicked.connect(self.deleteMachinePredictions)
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
            log.warning("User tried to logout but was already logged out.")
            pass
        event.accept()

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

        server = self.ui.serverLE.text()

        try:
            self.msgr = ManagerMessenger(server)
            server_ver_str = self.msgr.start()
            self.ui.infoLabel.setText(server_ver_str)
        except PlomBenignException as e:
            WarnMsg(self, "Could not connect to server.", info=str(e)).exec()
            self.msgr = None  # reset to avoid Issue #1622
            return

        try:
            self.msgr.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            WarnMsg(
                self,
                "Could not authenticate due to API mismatch. "
                f"Your client version is {__version__}. "
                "Error message from server is:",
                info=str(e),
            ).exec()
            self.msgr = None  # reset to avoid Issue #1622
            return
        except PlomExistingLoginException:
            msg = WarningQuestion(
                self,
                "You appear to be already logged in!\n\n"
                "  * Perhaps a previous session crashed?\n"
                "  * Do you have another client running,\n"
                "    e.g., on another computer?\n\n"
                "Should I force-logout the existing authorisation?"
                " (and then you can try to log in again)\n\n"
                "The other client will likely crash.",
            )
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.msgr.clearAuthorisation("manager", pwd)
                self.msgr = None
                self.login()
                return
            self.msgr = None  # reset to avoid Issue #1622
            return
        except PlomAuthenticationException as e:
            InfoMsg(self, "Could not authenticate:", info=e).exec()
            self.msgr = None  # reset to avoid Issue #1622
            return

        if not self.msgr.is_legacy_server():
            WarnMsg(
                self,
                "This deprecated tool only works on legacy servers.  "
                "Instead, try connecting to the server with your webbrowser.",
            ).exec()
            self.msgr = None  # reset to avoid Issue #1622
            return

        self.initial_login()
        self._enable_downloader()

    def initial_login(self):
        self.ui.userGBox.setEnabled(False)
        self.ui.serverGBox.setEnabled(False)
        self.ui.loginButton.setEnabled(False)
        self.ui.configTab.setEnabled(True)
        self.ui.userAllTab.setEnabled(True)
        self.initUserTab()
        # self.initConfigTab()
        try:
            self.getTPQV()
        except PlomServerNotReady:
            return
        self.ui.scanningAllTab.setEnabled(True)
        self.ui.progressAllTab.setEnabled(True)
        self.ui.reviewAllTab.setEnabled(True)
        self.ui.solnTab.setEnabled(True)

        self.initScanTab()
        self.initProgressTab()
        self.initReviewTab()
        self.initSolutionTab()

    def getTPQV(self):
        info = self.msgr.get_spec()
        exam_info = self.msgr.get_exam_info()
        self.max_papernum = exam_info["current_largest_paper_num"]
        self.numberOfPages = info["numberOfPages"]
        self.numberOfQuestions = info["numberOfQuestions"]
        self.numberOfVersions = info["numberOfVersions"]
        # Issue #2260
        self.qlabels = [
            get_question_label(info, n) for n in range(1, self.numberOfQuestions + 1)
        ]
        # which test pages are which type "id", "dnm", or "qN"
        self.testPageTypes = {info["idPage"]: "id"}
        for pg in info["doNotMarkPages"]:
            self.testPageTypes[pg] = "dnm"
        for q in range(1, info["numberOfQuestions"] + 1):
            for pg in info["question"][str(q)]["pages"]:
                self.testPageTypes[pg] = f"q{q}"

    ##################
    # config tab stuff

    def refreshConfig(self):
        check_mark = "\N{CHECK MARK}"
        cross = "\N{MULTIPLICATION SIGN}"
        try:
            spec = self.msgr.get_spec()
        except PlomServerNotReady as e:
            txt = cross + f"server not ready: {e}"
            spec = None
        else:
            txt = "<p>" + check_mark + " server has a spec: "
            txt += f"&ldquo;{spec['longName']}&rdquo;.</p>"
        self.ui.statusSpecLabel.setText(txt)

        try:
            classlist = self.msgr.IDrequestClasslist()
        except PlomServerNotReady as e:
            txt = cross + f"Server not ready: {e}"
        else:
            txt = check_mark + f" {len(classlist)} names in the classlist."
        self.ui.statusClasslistLabel.setText(txt)

        vmap = self.msgr.getGlobalQuestionVersionMap()
        if len(vmap) > 0:
            txt = check_mark + f" {len(vmap)} rows in the papers table."
        else:
            txt = "No rows have been inserted in the papers table,"
        self.ui.statusDatabaseLabel.setText(txt)

    def viewSpec(self):
        from plom import SpecVerifier

        try:
            spec_dict = self.msgr.get_spec()
        except (PlomServerNotReady, PlomConflict, ValueError) as e:
            WarnMsg(self, "Could not get spec.", info=e).exec()
            return
        sv = SpecVerifier(spec_dict)
        txt = "<p>Server's spec is shown below. The <tt>.toml</tt> format "
        txt += "is given below under &ldquo;details&rdquo;.</p>"
        info = str(sv)
        spec_toml = sv.as_toml_string()
        InfoMsg(self, txt, info=info, details=spec_toml).exec()
        self.refreshConfig()

    def uploadSpec(self):
        # TODO: on gnome "" is not cwd... str(Path.cwd()
        # options=QFileDialog.Option.DontUseNativeDialog
        # TODO: str(Path.cwd() / "testSpec.toml")
        fname, ftype = QFileDialog.getOpenFileName(
            self, "Get server spec file", None, "TOML files (*.toml)"
        )
        if fname == "":
            return
        fname = Path(fname)
        if not fname.is_file():
            return
        from plom import SpecVerifier

        sv = SpecVerifier.from_toml_file(fname)
        try:
            sv.verifySpec()
        except ValueError as e:
            WarnMsg(self, "Spec not valid", info=e).exec()
            return
        sv.checkCodes()
        try:
            self.msgr.upload_spec(sv.spec)
        except (PlomConflict, ValueError) as e:
            WarnMsg(self, "Could not accept a new spec", info=e).exec()
            return
        self.refreshConfig()

    def uploadClasslist(self):
        from plom.create import process_classlist_file, upload_classlist

        fname, ftype = QFileDialog.getOpenFileName(
            self, "Get classlist", None, "CSV files (*.csv)"
        )
        if fname == "":
            return
        fname = Path(fname)
        if not fname.is_file():
            return

        ignore_warnings = self.ui.classlistIgnoreWarningsCB.isChecked()
        force_upload = self.ui.classlistForceUploadCB.isChecked()

        # A copy-paste job from plom.create.__main__:
        try:
            spec = self.msgr.get_spec()
        except PlomServerNotReady as e:
            WarnMsg(self, "Server not ready.", info=e).exec()
            return
        success, classlist = process_classlist_file(
            fname, spec, ignore_warnings=ignore_warnings
        )
        if not success:
            WarnMsg(
                self, "Problems parsing classlist?", info="TODO: for now, check stdout?"
            ).exec()
            return
        try:
            upload_classlist(classlist, msgr=self.msgr, force=force_upload)
        except (PlomConflict, PlomRangeException, PlomServerNotReady) as e:
            WarnMsg(self, "Problem uploading classlist?", info=e).exec()
            return
        self.refreshConfig()

    def makeDataBase(self):
        from plom.create import build_database

        self.Qapp.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.Qapp.processEvents()

        try:
            build_database(msgr=self.msgr)
        except (PlomServerNotReady, PlomExistingDatabase) as e:
            # WarnMsg(self, "Could not build database", info=e).exec()
            self.ui.statusDatabaseLabel.setText(str(e))
            return
        finally:
            self.Qapp.restoreOverrideCursor()
            self.setEnabled(True)
        self.refreshConfig()

    def buildPapersChooseFolder(self):
        dur = QFileDialog.getExistingDirectory(
            self,
            "Choose a directory for building PDFs",
            None,
            QFileDialog.Option.ShowDirsOnly,
        )
        if dur == "":
            return
        dur = Path(dur)
        log.info("User explicitly chose %s for building papers", dur)
        self.ui.makePapersFolderLineEdit.setText(str(dur))

    def buildPapers(self):
        from plom.create import build_papers

        # TODO: better to display progress bar, for now tqdm appears on stdout
        self.Qapp.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.Qapp.processEvents()

        where = Path(self.ui.makePapersFolderLineEdit.text())
        which = self.ui.makePapersWhichSpinBox.value()
        if self.ui.radioButtonProduceAll.isChecked():
            which = None
        xpos = self.ui.makePapersXPosSpinBox.value()
        ypos = self.ui.makePapersYPosSpinBox.value()
        try:
            build_papers(
                basedir=where,
                fakepdf=False,
                no_qr=False,
                indexToMake=which,
                xcoord=xpos,
                ycoord=ypos,
                msgr=self.msgr,
            )
        except (
            PlomServerNotReady,
            PlomConflict,
            OSError,
            RuntimeError,
            ValueError,
        ) as e:
            # fitz.FileNotFoundError is a subclass of RuntimeError
            self.Qapp.restoreOverrideCursor()
            WarnMsg(
                self,
                "<p>Could not build papers. The following error message was given:</p>",
                info=e,
                details=f"Working directory: {where}\nError type: {type(e)}",
            ).exec()
        self.Qapp.restoreOverrideCursor()
        self.setEnabled(True)

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
        self.refreshUnknownList()
        self.refreshCList()
        self.refreshDiscardList()
        # too slow on large servers, causing timeouts
        # self.refreshDangList()

    def initScanStatusTab(self):
        self.ui.scanTW.setHeaderLabels(["Test number", "Page number", "Version"])
        self.ui.scanTW.activated.connect(self.viewSPage)
        self.ui.incompTW.setHeaderLabels(["Test number", "Page", "Version", "Status"])
        self.ui.incompTW.activated.connect(self.viewISTest)
        self.refresh_scan_status_lists()

    def refresh_scan_status_lists(self):
        numI = self._refreshIList()
        numS = self._refreshSList()
        countstr = str(numI + numS)
        countstr += "*" if numI != 0 else "\N{CHECK MARK}"
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
            for p, v, s in incomplete[t]:
                if s:
                    l0.addChild(QTreeWidgetItem(["", str(p), str(v), "scanned"]))
                else:
                    it = QTreeWidgetItem(["", str(p), str(v), "missing"])
                    it.setBackground(3, QBrush(QColor(255, 0, 0, 48)))
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
            for p, v in scanned[t]:
                l1 = QTreeWidgetItem(["", str(p), str(v)])
                if "{}.{}".format(t, p) in cdtp.values():
                    l0.setBackground(0, QBrush(QColor(0, 255, 255, 48)))
                    l0.setToolTip(0, "Has collisions")
                    l1.setBackground(1, QBrush(QColor(0, 255, 255, 48)))
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
            pagedata = self.msgr.getTPageImageData(t, p, v)
        elif pdetails[0] == "h":  # is a hw-page = h.q.o
            q = pdetails.split(".")[1]
            o = pdetails.split(".")[2]
            pagedata = self.msgr.getHWPageImageData(t, q, o)
        elif pdetails[0] == "e":  # is a extra-page = e.q.o
            q = pdetails.split(".")[1]
            o = pdetails.split(".")[2]
            pagedata = self.msgr.getEXPageImageData(t, q, o)
        else:
            return

        if not pagedata:
            return
        pagedata = self.downloader.sync_downloads(pagedata)
        GroupView(self, pagedata).exec()

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
            if msg.exec() == QMessageBox.StandardButton.No:
                return
            try:
                msg = self.msgr.removeSinglePage(test_number, page_name)
                InfoMsg(self, msg).exec()
            except PlomConflict as e:
                WarnMsg(self, "Could not remove page", info=e).exec()
        else:
            test_number = int(pvi[0].text(0))  # grab test number
            msg = WarningQuestion(
                self,
                f"Will remove all scanned pages from the selected test - test number {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec() == QMessageBox.StandardButton.No:
                return

            rval = self.msgr.removeAllScannedPages(test_number)
            # Cleanup, Issue #2141
            InfoMsg(self, "{}".format(rval)).exec()
        self.refresh_scan_status_lists()

    def substituteTestQuestionPage(self, test_number, page_number, question, version):
        msg = SimpleQuestion(
            self,
            'Are you sure you want to substitute a "Missing Page" blank for '
            f"tpage {page_number} of question {question} test {test_number}?",
        )
        if msg.exec() == QMessageBox.StandardButton.No:
            return
        s = self.msgr.replaceMissingTestPage(test_number, page_number, version)
        InfoMsg(self, "Successfully substituted.", info=s).exec()

    def substituteTestDNMPage(self, test_number, page_number):
        msg = SimpleQuestion(
            self,
            'Are you sure you want to substitute a "Missing Page" blank for '
            f"tpage {page_number} of test {test_number} - it is a Do Not Mark page?",
        )
        if msg.exec() == QMessageBox.StandardButton.No:
            return

        try:
            self.msgr.replaceMissingDNMPage(test_number, page_number)
        except (PlomConflict, PlomNoPaper) as e:
            InfoMsg(self, f"{e}").exec()

    def substituteAllDNMPages(self):
        spec = self.msgr.get_spec()
        dnm_pages = spec["doNotMarkPages"]
        if not dnm_pages:
            InfoMsg(
                self,
                "There are no do-not-mark pages in the spec.",
                details="\n".join(f"{k}: {v}" for k, v in spec.items()),
            ).exec()
            return
        msg = SimpleQuestion(
            self,
            "Bulk forgive all missing DNM pages?",
            question=f"""
                <p>Do-not-mark ("DNM") pages are not likely to be marked so
                its no issue if they are not here.  For example, they might
                be formula sheets.  This option will substitute a "Missing
                Page" placeholder for all such pages, for any test that is
                partially uploaded.</p>
                <p>This assessment has DNM pages:
                {", ".join(str(n) for n in dnm_pages)}<br />
                (Other pages and pages of unused tests will be uneffected.)</p>
                <p>Would you like to continue substituting missing DNM pages?</p>
            """,
        )
        if msg.exec() == QMessageBox.StandardButton.No:
            return

        incomplete = self.msgr.getIncompleteTests()  # triples [p, v, true/false]
        output_log = "Output log:"
        subs = []
        for papernum, X in incomplete.items():
            papernum = int(papernum)
            # [['t.1', 1, True], ['t.2', 1, False], ['t.3', 1, True], ...]
            for pagestr, version, scanned in X:
                if not scanned:
                    for p in dnm_pages:
                        if f"t.{p}" == pagestr:
                            subs.append(papernum)
                            b = f"replacing {papernum:04} DNM pg {pagestr}:"
                            s = self.msgr.replaceMissingDNMPage(papernum, p)
                            output_log += "\n" + b + " " + s

        InfoMsg(
            self,
            f"Finished forgiving missing DNM pages: made {len(subs)} substitutions.",
            info="Paper numbers: " + format_int_list_with_runs(subs),
            info_pre=False,
            details=output_log,
        ).exec()
        self.refresh_scan_status_lists()

    def autogenerateIDPage(self, test_number):
        msg = SimpleQuestion(
            self,
            f"Are you sure you want to generate an ID for test {test_number}? "
            "You can only do this for homeworks or pre-named tests.",
        )
        if msg.exec() == QMessageBox.StandardButton.No:
            return
        try:
            rval = self.msgr.replaceMissingIDPage(test_number)
            # Cleanup, Issue #2141
            InfoMsg(self, "{}".format(rval)).exec()
        except PlomUnidentifiedPaperException as err:
            WarnMsg(self, str(err)).exec()

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
        if msg.exec() == QMessageBox.StandardButton.No:
            return
        try:
            rval = self.msgr.replaceMissingHWQuestion(
                student_id=None, test=test_number, question=question
            )
            # Cleanup, Issue #2141
            InfoMsg(self, "{}".format(rval)).exec()
        except PlomTakenException as e:
            WarnMsg(self, "That question already has hw pages present.", info=e).exec()

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
            if msg.exec() == QMessageBox.StandardButton.No:
                return

            try:
                s = self.msgr.removeSinglePage(test_number, page_name)
                InfoMsg(self, s).exec()
            except PlomConflict as e:
                WarnMsg(self, "Could not remove page", info=e).exec()
        else:
            test_number = int(pvi[0].text(0))  # grab test number
            msg = WarningQuestion(
                self,
                f"Will remove all scanned pages from the selected test - test number {test_number}.",
                "Are you sure you wish to do this? (not reversible)",
            )
            if msg.exec() == QMessageBox.StandardButton.No:
                return

            rval = self.msgr.removeAllScannedPages(test_number)
            # Cleanup, Issue #2141
            WarnMsg(self, "{}".format(rval)).exec()
        self.refresh_scan_status_lists()

    def initUnknownTab(self):
        self.unknownModel = QStandardItemModel(0, 8)
        self.ui.unknownTV.setModel(self.unknownModel)
        self.ui.unknownTV.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.unknownTV.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.unknownModel.setHorizontalHeaderLabels(
            [
                "ID",
                "File",
                "Bundle name",
                "Bundle position",
                "Action to be taken",
                "Rotation-angle",
                "Paper number",
                "Page or Question indices",
            ]
        )
        self.ui.unknownTV.setIconSize(QSize(32, 32))
        self.ui.unknownTV.activated.connect(self.viewUnknownPage)
        self.ui.unknownTV.setColumnHidden(0, True)
        self.refreshUnknownList()

    def refreshUnknownList(self):
        self.unknownModel.removeRows(0, self.unknownModel.rowCount())
        self.ui.unknownTV.setSortingEnabled(False)
        unknowns = self.msgr.getUnknownPages()
        # We don't have proper sorting in this table: Issues #2414, #2067
        # We can at least initially populate it in a meaningful way!
        unknowns = sorted(
            unknowns, key=lambda x: (x["bundle_name"], x["bundle_position"])
        )
        for r, u in enumerate(unknowns):
            it0 = QStandardItem(Path(u["server_path"]).name)
            pm = QPixmap()
            res = resources.files(plom.client.icons) / "manager_unknown.svg"
            pm.loadFromData(res.read_bytes())
            it0.setIcon(QIcon(pm))
            it1 = QStandardItem("?")
            it1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it2 = QStandardItem(str(u["orientation"]))
            it2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it3 = QStandardItem("")
            it3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it4 = QStandardItem("")
            it4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # the displayed value in first column:
            raw = QStandardItem(str(u["id"]))
            # but store entire dict in first entry, may need wrapped in QVariant
            raw.setData(u)
            self.unknownModel.insertRow(
                r,
                [
                    raw,
                    it0,
                    QStandardItem(u["bundle_name"]),
                    QStandardItem(str(u["bundle_position"])),
                    it1,
                    it2,
                    it3,
                    it4,
                ],
            )
        self.ui.unknownTV.resizeRowsToContents()
        self.ui.unknownTV.resizeColumnsToContents()

        countstr = str(len(unknowns))
        countstr += "*" if countstr != "0" else "\N{CHECK MARK}"
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.unknownTab),
            f"&Unknown Pages ({countstr})",
        )
        # Issue #2414: this would mess up the careful manual sort we did above
        # self.ui.unknownTV.setSortingEnabled(True)

    def viewUnknownPage(self):
        pvi = self.ui.unknownTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        pagedatum = self.unknownModel.item(r, 0).data()  # .toPyObject?
        pagedatum = self.downloader.sync_download(pagedatum)
        # get the list of ID'd papers
        iDict = self.msgr.getIdentified()
        uvw = UnknownViewWindow(
            self,
            [pagedatum],
            [self.max_papernum, self.numberOfPages, self.qlabels],
            iDict,
        )
        if uvw.exec() == QDialog.DialogCode.Accepted:
            # Colin hates all these hardcoded integers!
            self.unknownModel.item(r, 4).setText(uvw.action)
            self.unknownModel.item(r, 5).setText("{}".format(uvw.get_orientation()))
            self.unknownModel.item(r, 6).setText("{}".format(uvw.test))
            # questions is now of the form "1" or "1,2" or "1,2,3" etc
            self.unknownModel.item(r, 7).setText("{}".format(uvw.pq))
            if uvw.action == "discard":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_discard.svg"
                pm.loadFromData(res.read_bytes())
                self.unknownModel.item(r, 1).setIcon(QIcon(pm))
            elif uvw.action == "extra":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_extra.svg"
                pm.loadFromData(res.read_bytes())
                self.unknownModel.item(r, 1).setIcon(QIcon(pm))
            elif uvw.action == "test":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_test.svg"
                pm.loadFromData(res.read_bytes())
                self.unknownModel.item(r, 1).setIcon(QIcon(pm))
            elif uvw.action == "homework":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_hw.svg"
                pm.loadFromData(res.read_bytes())
                self.unknownModel.item(r, 1).setIcon(QIcon(pm))

    def doUActions(self):
        for r in range(self.unknownModel.rowCount()):
            action = self.unknownModel.item(r, 4).text()
            pagedata = self.unknownModel.item(r, 0).data()
            if action == "discard":
                self.msgr.removeUnknownImage(pagedata["server_path"])
            elif action == "extra":
                try:
                    # have to convert "1,2,3" into [1,2,3]
                    question_list = [
                        int(x) for x in self.unknownModel.item(r, 7).text().split(",")
                    ]
                    self.msgr.unknownToExtraPage(
                        pagedata["server_path"],
                        self.unknownModel.item(r, 6).text(),
                        question_list,
                        self.unknownModel.item(r, 5).text(),
                    )
                except PlomConflict as err:
                    WarnMsg(self, f"{err}").exec()
            elif action == "test":
                try:
                    if (
                        self.msgr.unknownToTestPage(
                            pagedata["server_path"],
                            self.unknownModel.item(r, 6).text(),
                            self.unknownModel.item(r, 7).text(),
                            self.unknownModel.item(r, 5).text(),
                        )
                        == "collision"
                    ):
                        WarnMsg(
                            self,
                            "Collision created in test {}".format(
                                self.unknownModel.item(r, 6).text()
                            ),
                        ).exec()
                except PlomConflict as err:
                    WarnMsg(self, f"{err}").exec()
            elif action == "homework":
                try:
                    # have to convert "1,2,3" into [1,2,3]
                    question_list = [
                        int(x) for x in self.unknownModel.item(r, 7).text().split(",")
                    ]
                    self.msgr.unknownToHWPage(
                        pagedata["server_path"],
                        self.unknownModel.item(r, 6).text(),
                        question_list,
                        self.unknownModel.item(r, 5).text(),
                    )
                except PlomConflict as err:
                    WarnMsg(self, f"{err}").exec()

            else:
                pass
        self.refreshScanTab()

    def viewWholeTest(self, testnum, parent=None):
        # TODO: used to get the ID page, and DNM etc, "just" need a new metadata

        # TODO: what was this vt None case here?
        # vt = self.msgr.getTestImages(testNumber)
        # if vt is None:
        #     return

        if parent is None:
            parent = self
        pagedata = self.msgr.get_pagedata(testnum)
        pagedata = self.downloader.sync_downloads(pagedata)
        labels = [x["pagename"] for x in pagedata]
        WholeTestView(testnum, pagedata, labels, parent=parent).exec()

    def checkTPage(self, testNumber, pageNumber, parent=None):
        if parent is None:
            parent = self
        cp = self.msgr.checkTPage(testNumber, pageNumber)
        # returns [v, image] or [v, imageBytes]
        if cp[1] is None:
            InfoMsg(
                parent,
                "Page {} of test {} is not scanned - should be version {}".format(
                    pageNumber, testNumber, cp[0]
                ),
            ).exec()
            return
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False).name)
        with open(f, "wb") as fh:
            fh.write(cp[1])
        GroupView(
            parent,
            [f],
            title=f"Paper {testNumber} page {pageNumber} already has an image",
            before_text="Existing image:",
            after_text=f"Performing this action would create a collision with paper {testNumber} p. {pageNumber}",
        ).exec()
        f.unlink()

    def initCollideTab(self):
        self.collideModel = QStandardItemModel(0, 6)
        self.ui.collideTV.setModel(self.collideModel)
        self.ui.collideTV.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.collideTV.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
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
            res = resources.files(plom.client.icons) / "manager_collide.svg"
            pm.loadFromData(res.read_bytes())
            it1.setIcon(QIcon(pm))
            it2 = QStandardItem("?")
            it2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it3 = QStandardItem("{}".format(colDict[u][0]))
            it3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it4 = QStandardItem("{}".format(colDict[u][1]))
            it4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it5 = QStandardItem("{}".format(colDict[u][2]))
            it5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.collideModel.insertRow(r, [QStandardItem(u), it1, it2, it3, it4, it5])
            r += 1
        self.ui.collideTV.resizeRowsToContents()
        self.ui.collideTV.resizeColumnsToContents()
        countstr = str(len(colDict.keys()))
        countstr += "*" if countstr != "0" else "\N{CHECK MARK}"
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

        (pagedata,) = self.msgr.getTPageImageData(test, page, version)
        vop = self.msgr.get_image(pagedata["id"], pagedata["md5"])
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
        if cvw.exec() == QDialog.DialogCode.Accepted:
            if cvw.action == "original":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_discard.svg"
                pm.loadFromData(res.read_bytes())
                self.collideModel.item(r, 1).setIcon(QIcon(pm))
                self.collideModel.item(r, 2).setText("discard")
            elif cvw.action == "collide":
                pm = QPixmap()
                res = resources.files(plom.client.icons) / "manager_test.svg"
                pm.loadFromData(res.read_bytes())
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
                except PlomConflict as err:
                    WarnMsg(self, f"{err}").exec()
            else:
                pass
                # print(
                #     "No action for file {}.".format(self.collideModel.item(r, 0).text())
                # )
        self.refreshCList()

    def initDiscardTab(self):
        self.discardModel = QStandardItemModel(0, 3)
        self.ui.discardTV.setModel(self.discardModel)
        self.ui.discardTV.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.discardTV.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.discardModel.setHorizontalHeaderLabels(
            [
                "ID",
                "File",
                "Reason discarded",
            ]
        )
        self.ui.discardTV.setIconSize(QSize(32, 32))
        self.ui.discardTV.activated.connect(self.viewDiscardPage)
        self.ui.discardTV.setColumnHidden(0, True)
        self.refreshDiscardList()

    def refreshDiscardList(self):
        self.discardModel.removeRows(0, self.discardModel.rowCount())
        discards = self.msgr.getDiscardedPages()
        for r, d in enumerate(discards):
            it1 = QStandardItem(Path(d["server_path"]).name)
            pm = QPixmap()
            res = resources.files(plom.client.icons) / "manager_none.svg"
            pm.loadFromData(res.read_bytes())
            it1.setIcon(QIcon(pm))
            it2 = QStandardItem(d["reason"])
            raw = QStandardItem(str(d["id"]))
            raw.setData(d)
            self.discardModel.insertRow(r, (raw, it1, it2))
        self.ui.discardTV.resizeRowsToContents()
        self.ui.discardTV.resizeColumnsToContents()
        self.ui.scanTabW.setTabText(
            self.ui.scanTabW.indexOf(self.ui.discardTab),
            "&Discarded Pages ({})".format(len(discards)),
        )

    def viewDiscardPage(self):
        pvi = self.ui.discardTV.selectedIndexes()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        pagedata = self.discardModel.item(r, 0).data()
        pagedata = self.downloader.sync_download(pagedata)
        if DiscardViewWindow(self, [pagedata]).exec() == QDialog.DialogCode.Accepted:
            # Scary, nicer to require img id?
            self.msgr.discardToUnknown(pagedata["server_path"])
            self.refreshDiscardList()

    def initDanglingTab(self):
        self.ui.labelDanglingExplain.setText(
            """
            <hr />
            <p>
              <center>
                <b>Caution:</b>
                Refreshing this can interfere with other users.
              </center>
            </p>
            <p>When there are a lot of papers (say 1000 or more) the API
            call that backs the feature is slow.  It would be best to use
            this feature only when your server is otherwise idle (no active
            scanning uploads and minimal marking activity).</p>
            <hr />
            <p>A page which is part of a test that is not yet completely
            scanned and uploaded will show up here as a
            <em>dangling page</em>.
            These should go away automatically once tests become complete.
            Note that this might require dealing with Unknown Pages,
            Collisions etc.</p>
            <p>
            If you have already assigned all extra pages etc and there
            are still dangling pages, then this might indicates that you
            have mis-assigned an extra page to a test that has not
            actually in use.</p>
            """
        )
        self.ui.labelDanglingExplain.setWordWrap(True)
        self.danglingModel = QStandardItemModel(0, 5)
        self.ui.danglingTV.setModel(self.danglingModel)
        self.ui.danglingTV.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.danglingTV.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.danglingModel.setHorizontalHeaderLabels(
            (
                "Type",
                "Test",
                "Group",
                "Code",
                "Page / Order",
                "Bundle name",
                "Bundle position",
            )
        )
        self.ui.danglingTV.activated.connect(self.viewDanglingPage)
        # Too slow on large servers, causing timeouts
        # self.refreshDangList()

    def refreshDangList(self):
        self.danglingModel.removeRows(0, self.danglingModel.rowCount())
        # list of dicts
        danglers = self.msgr.getDanglingPages()
        for r, dang in enumerate(danglers):
            it0 = QStandardItem(f"{dang['type']}")
            it1 = QStandardItem(f"{dang['test']}")
            it2 = QStandardItem(f"{dang['group']}")
            it3 = QStandardItem(f"{dang['code']}")
            if dang["type"] == "tpage":
                it4 = QStandardItem(f"{dang['page']}")
            else:
                it4 = QStandardItem(f"{dang['order']}")
            it5 = QStandardItem(f"{dang['bundle_name']}")
            it6 = QStandardItem(f"{dang['bundle_order']}")
            self.danglingModel.insertRow(r, (it0, it1, it2, it3, it4, it5, it6))
        self.ui.danglingTV.resizeRowsToContents()
        self.ui.danglingTV.resizeColumnsToContents()

        countstr = str(len(danglers))
        countstr += "*" if countstr != "0" else "\N{CHECK MARK}"
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
        if msg.exec() == QMessageBox.StandardButton.No:
            return

        try:
            s = self.msgr.removeSinglePage(test_number, page_name)
            InfoMsg(self, s).exec()
        except PlomConflict as e:
            WarnMsg(self, "Could not remove page", info=e).exec()

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
            [
                "Test number",
                "Scanned",
                "Identified",
                "Questions Marked",
                "Last Update (UTC)",
            ]
        )
        self.ui.overallTW.activated.connect(self.viewTestStatus)
        self.ui.overallTW.resizeRowsToContents()
        self.ui.overallTW.setSortingEnabled(True)
        self.refreshOverallTab()

    def downloadCSV(self):
        from plom.finish import CSVFilename, pull_spreadsheet

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", CSVFilename, "Comma Separated Values (*.csv)"
        )
        if not filename:
            return
        if not pull_spreadsheet(msgr=self.msgr, filename=filename, verbose=False):
            WarnMsg(
                self,
                f"Spreadsheet written to {filename} but grading is not complete.",
                info="Either some papers are unidentified or they are not fully marked.",
                info_pre=False,
            ).exec()

    def viewTestStatus(self):
        pvi = self.ui.overallTW.selectedItems()
        if len(pvi) == 0:
            return
        r = pvi[0].row()
        testNumber = int(self.ui.overallTW.item(r, 0).text())
        stats = self.msgr.RgetStatus(testNumber)
        TestStatus(self, self.qlabels, stats).exec()

    def refreshOverallTab(self):
        self.ui.overallTW.clearContents()
        self.ui.overallTW.setRowCount(0)

        opDict = self.msgr.RgetCompletionStatus()

        # TODO: why not let Qt do it for us...?
        tk = list(opDict.keys())
        tk.sort(key=int)  # sort in numeric order
        # each dict value is [Scanned, Identified, #Marked, LastUpdate]

        self.ui.overallTW.setSortingEnabled(False)
        for r, t in enumerate(tk):
            # for some reason t is string instead of an int
            tstr = str(t)
            t = int(t)
            self.ui.overallTW.insertRow(r)
            item = QTableWidgetItem()
            assert isinstance(t, int)
            item.setData(Qt.ItemDataRole.DisplayRole, t)
            self.ui.overallTW.setItem(r, 0, item)

            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, opDict[tstr][0])
            if opDict[tstr][0]:
                item.setBackground(QBrush(QColor(0, 255, 0, 48)))
                item.setToolTip("Has been scanned")
            elif opDict[tstr][2] > 0:
                item.setBackground(QBrush(QColor(255, 0, 0, 48)))
                item.setToolTip("Has been (part-)marked but not completely scanned.")
            self.ui.overallTW.setItem(r, 1, item)

            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, opDict[tstr][1])
            if opDict[tstr][1]:
                item.setBackground(QBrush(QColor(0, 255, 0, 48)))
                item.setToolTip("Has been identified")
            self.ui.overallTW.setItem(r, 2, item)

            item = QTableWidgetItem()
            assert isinstance(opDict[tstr][2], int)
            item.setData(Qt.ItemDataRole.DisplayRole, opDict[tstr][2])
            if opDict[tstr][2] == self.numberOfQuestions:
                item.setBackground(QBrush(QColor(0, 255, 0, 48)))
                item.setToolTip("Has been marked")
            self.ui.overallTW.setItem(r, 3, item)

            item = QTableWidgetItem()
            assert isinstance(opDict[tstr][3], str)
            time = arrow.get(opDict[tstr][3])
            item.setData(Qt.ItemDataRole.DisplayRole, arrowtime_to_simple_string(time))
            item.setToolTip(time.humanize())
            self.ui.overallTW.setItem(r, 4, item)
        self.ui.overallTW.setSortingEnabled(True)

    def initIDTab(self):
        self.refreshIDTab()
        self.ui.idPB.setFormat("%v / %m")
        self.ui.predictionTW.setColumnCount(6)
        self.ui.predictionTW.setHorizontalHeaderLabels(
            ("Test", "Student ID", "Name", "Predicted ID", "Predictor", "Certainty")
        )
        self.ui.predictionTW.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.ui.predictionTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        # Seemed broken so commented out
        # self.ui.predictionTW.setAlternatingRowColors(True)
        self.ui.predictionTW.activated.connect(self.viewIDPage)

    def refreshIDTab(self):
        ti = self.msgr.IDprogressCount()
        self.ui.idPB.setValue(ti[0])
        self.ui.idPB.setMaximum(ti[1])
        self.getPredictions()

    def selectRectangle(self):
        try:
            imageList = self.msgr.IDgetImageFromATest()
        except PlomNoMoreException as err:
            InfoMsg(self, "No unIDd images to show.", info=err).exec()
            return
        with tempfile.TemporaryDirectory() as td:
            inames = []
            for i, img_bytes in enumerate(imageList):
                img_ext = "unknown_ext"
                tmp = Path(td) / "id.{}.{}".format(i, img_ext)
                with open(tmp, "wb") as fh:
                    fh.write(img_bytes)
                inames.append(tmp)
            srw = SelectRectangleWindow(self, inames)
            if srw.exec() == QDialog.DialogCode.Accepted:
                top, bottom = srw.top_bottom_values
                self.ui.cropTopLE.setText(str(100 * top))
                self.ui.cropBottomLE.setText(str(100 * bottom))

    def viewIDPage(self):
        idx = self.ui.predictionTW.selectedIndexes()
        if len(idx) == 0:
            return
        test = self.ui.predictionTW.item(idx[0].row(), 0).data(
            Qt.ItemDataRole.DisplayRole
        )
        # TODO: should we populate with empty string to avoid dealing with None here?
        sid = self.ui.predictionTW.item(idx[0].row(), 1)
        if sid is not None:
            sid = sid.data(Qt.ItemDataRole.DisplayRole)
        pred_sid = self.ui.predictionTW.item(idx[0].row(), 3)
        if pred_sid is not None:
            pred_sid = pred_sid.data(Qt.ItemDataRole.DisplayRole)
        certainty = self.ui.predictionTW.item(idx[0].row(), 5)
        if certainty is not None:
            certainty = certainty.data(Qt.ItemDataRole.DisplayRole)

        with tempfile.TemporaryDirectory() as td:
            pagedata = self.msgr.get_pagedata(test)
            id_pages = []
            for row in pagedata:
                # Issue #2707: better use a image-type key
                if not row["pagename"].casefold().startswith("id"):
                    continue
                img_bytes = self.msgr.get_image(row["id"], row["md5"])
                ext = Path(row["server_path"]).suffix
                filename = Path(td) / f'img_{int(test):04}_{row["pagename"]}{ext}'
                with open(filename, "wb") as fh:
                    fh.write(img_bytes)
                id_pages.append(filename)
            if not id_pages:
                return
            assert len(id_pages) == 1, "Expected at most one ID page"
            (img_name,) = id_pages

            if sid is None and pred_sid is not None:
                title = f"ID page: predicted as {pred_sid} certainty {certainty}"
            elif sid == pred_sid:
                title = f"ID page: IDed as {sid}"
            else:
                title = f"ID page: IDed as {sid} but predicted as {pred_sid} certainty {certainty}"
            GroupView(self, img_name, title=title).exec()

    def id_reader_get_log(self):
        is_running, timestamp, msg = self.msgr.id_reader_get_logs()
        if is_running:
            label = "<em>Running</em>"
        elif timestamp is None:
            label = "Never run"
        else:
            label = "Stopped"
        if timestamp:
            timestamp = arrow.get(timestamp)
            label += f", started {timestamp.humanize()}"
            label += f' {timestamp.isoformat(" ", "seconds")}.'
        label = f"<p>{label}<br />Log output:</p>"
        self.ui.idReaderStatusLabel.setText(label)
        self.ui.idReaderLogTextEdit.setPlainText(msg)

    def id_reader_run(self, ignore_timestamp=False):
        is_running, new_start, timestamp = self.msgr.id_reader_run(
            float(self.ui.cropTopLE.text()) / 100,
            float(self.ui.cropBottomLE.text()) / 100,
            ignore_timestamp=ignore_timestamp,
        )
        if is_running:
            if new_start:
                txt = "IDReader launched in background."
                info = """
                    <p>It may take some time to run; click &ldquo;refresh&rdquo;
                    to update output.</p>
                """
            else:
                timestamp = arrow.get(timestamp)
                txt = "IDReader currently running,"
                txt += f" launched {timestamp.humanize()} at"
                txt += f' {timestamp.isoformat(" ", "seconds")}.'
                info = """
                    <p>If its been a while or output is unexpected, perhaps it
                    crashed.</p>
                """
            InfoMsg(self, txt, info=info, info_pre=False).exec()
            self.id_reader_get_log()
            return
        else:
            timestamp = arrow.get(timestamp)
            msg = SimpleQuestion(
                self,
                f"IDReader was last run {timestamp.humanize()} at"
                f' {timestamp.isoformat(" ", "seconds")}.',
                question="Do you want to rerun it?",
            )
            if msg.exec() == QMessageBox.StandardButton.No:
                return
            self.id_reader_run(ignore_timestamp=True)

    def id_reader_kill(self):
        if (
            SimpleQuestion(self, "Stop running process", "Are you sure?").exec()
            == QMessageBox.StandardButton.No
        ):
            return
        msg = self.msgr.id_reader_kill()
        txt = "Stopped background ID reader process.  Server response:"
        InfoMsg(self, txt, info=msg).exec()

    def run_predictor(self):
        try:
            status = self.msgr.run_predictor()
            InfoMsg(self, "Results of ID matching:", info=status).exec()
        except PlomConflict as e:
            WarnMsg(self, "ID matching procedure failed:", info=f"{e}").exec()
        self.getPredictions()

    def un_id_paper(self):
        idx = self.ui.predictionTW.selectedIndexes()
        if not idx:
            return
        test = self.ui.predictionTW.item(idx[0].row(), 0).data(
            Qt.ItemDataRole.DisplayRole
        )
        iDict = self.msgr.getIdentified()
        msg = f"Do you want to reset the ID of test number {test}?"
        if str(test) in iDict:
            sid, sname = iDict[str(test)]
            msg += f"\n\nCurrently is {sid}: {sname}"
        else:
            msg += "\n\nCan't find current ID - is likely not ID'd yet."
        if SimpleQuestion(self, msg).exec() == QMessageBox.StandardButton.No:
            return
        self.msgr.un_id_paper(test)
        self.getPredictions()

    def remove_id_prediction(self):
        idx = self.ui.predictionTW.selectedIndexes()
        if not idx:
            return
        # TODO: replace with loop over multiple row selections?
        assert len(idx) == 6
        idx = idx[0]  # they all have the same row
        test = self.ui.predictionTW.item(idx.row(), 0).data(Qt.ItemDataRole.DisplayRole)
        cell = self.ui.predictionTW.item(idx.row(), 4)
        if cell is None:
            InfoMsg(
                self,
                f"Selected row index {idx.row()} seems to have no prediction to remove",
            ).exec()
            return
        predictor = cell.data(Qt.ItemDataRole.DisplayRole)
        msg = f'Do you want to remove "{predictor}" predicted ID of test number {test}?'
        if SimpleQuestion(self, msg).exec() == QMessageBox.StandardButton.No:
            return
        if predictor == "prename":
            self.msgr.remove_pre_id(test)
        else:
            ErrorMsg(self, "Sorry removing non-prename not implemented yet").exec()
            # TODO: kwarg not implemented yet
            # self.msgr.remove_id_prediction(test, predictor=predictor)
        self.getPredictions()

    def getPredictions(self):
        prename_predictions = self.msgr.IDgetPredictionsFromPredictor("prename")
        lap_predictions = self.msgr.IDgetPredictionsFromPredictor("MLLAP")
        greedy_predictions = self.msgr.IDgetPredictionsFromPredictor("MLGreedy")
        identified = self.msgr.getIdentified()

        self.ui.predictionTW.clearContents()
        self.ui.predictionTW.setRowCount(0)

        self.ui.predictionTW.setSortingEnabled(False)

        # TODO: Issue #1745
        # TODO: all existing papers or scanned only?
        alltests = range(1, self.max_papernum + 1)

        r = 0
        for t in alltests:
            identity = identified.get(str(t), None)
            prename = prename_predictions.get(str(t), None)
            lap = lap_predictions.get(str(t), None)
            greedy = greedy_predictions.get(str(t), None)

            hilite_id = False
            if prename and identity:
                if prename["student_id"] != identity[0]:
                    # TODO: highlight identified if not matching prename, after #2081
                    hilite_id = True
            hilite = False
            if lap and greedy:
                if lap["student_id"] != greedy["student_id"]:
                    hilite = True

            predictions_to_add = [prename, lap, greedy]

            if not any(predictions_to_add) and identity:
                self.ui.predictionTW.insertRow(r)
                # put in the test-number
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, int(t))
                self.ui.predictionTW.setItem(r, 0, item)

                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, identity[0])
                item.setToolTip("Has been identified")
                self.ui.predictionTW.setItem(r, 1, item)

                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, identity[1])
                item.setToolTip("Has been identified")
                self.ui.predictionTW.setItem(r, 2, item)
                r += 1
                continue

            for pred in predictions_to_add:
                if pred is not None:
                    self.ui.predictionTW.insertRow(r)
                    # put in the test-number
                    item = QTableWidgetItem()
                    item.setData(Qt.ItemDataRole.DisplayRole, int(t))
                    self.ui.predictionTW.setItem(r, 0, item)

                    item0 = QTableWidgetItem()
                    item0.setData(Qt.ItemDataRole.DisplayRole, pred["student_id"])
                    self.ui.predictionTW.setItem(r, 3, item0)
                    item1 = QTableWidgetItem()
                    item1.setData(Qt.ItemDataRole.DisplayRole, pred["predictor"])
                    self.ui.predictionTW.setItem(r, 4, item1)
                    item2 = QTableWidgetItem()
                    # round certainty for display
                    item2.setData(
                        Qt.ItemDataRole.DisplayRole, round(pred["certainty"], 3)
                    )
                    self.ui.predictionTW.setItem(r, 5, item2)

                    if identity:
                        item = QTableWidgetItem()
                        item.setData(Qt.ItemDataRole.DisplayRole, identity[0])
                        item.setToolTip("Has been identified")
                        self.ui.predictionTW.setItem(r, 1, item)
                        if hilite_id:
                            item.setBackground(QBrush(QColor(255, 0, 0, 48)))
                        item = QTableWidgetItem()
                        item.setData(Qt.ItemDataRole.DisplayRole, identity[1])
                        item.setToolTip("Has been identified")
                        self.ui.predictionTW.setItem(r, 2, item)

                    if identity:
                        if hilite_id:
                            item0.setBackground(QBrush(QColor(255, 0, 0, 48)))
                            item1.setBackground(QBrush(QColor(255, 0, 0, 48)))
                            item2.setBackground(QBrush(QColor(255, 0, 0, 48)))
                        else:
                            # prediction less important but perhaps not irrelevant
                            item0.setBackground(QBrush(QColor(128, 128, 128, 48)))
                            item1.setBackground(QBrush(QColor(128, 128, 128, 48)))
                            item2.setBackground(QBrush(QColor(128, 128, 128, 48)))
                            # This doesn't work
                            # item0.setEnabled(False)
                    else:
                        # TODO: colour-code based on confidence?
                        if hilite:
                            item0.setBackground(QBrush(QColor(0, 255, 255, 48)))
                            item1.setBackground(QBrush(QColor(0, 255, 255, 48)))
                            item2.setBackground(QBrush(QColor(0, 255, 255, 48)))
                    r += 1

        self.ui.predictionTW.setSortingEnabled(True)

    def deleteMachinePredictions(self):
        msg = SimpleQuestion(
            self,
            "Delete the auto-read predicted IDs?"
            " (note that this does not delete user-confirmed IDs or"
            " prenamed predictions)",
        )
        if msg.exec() == QMessageBox.StandardButton.No:
            return
        # TODO: likely unnecessary?
        self.msgr.ID_delete_machine_predictions()
        # Instead we can just do:
        # self.msgr.ID_delete_predictions_from_predictor(predictor="MLLAP")
        # self.msgr.ID_delete_predictions_from_predictor(predictor="MLGreedy")
        self.getPredictions()

    def initMarkTab(self):
        # initialise the widgets without the actual stats
        grid = QGridLayout()
        self.pd = {}
        for qidx in range(1, self.numberOfQuestions + 1):
            qlabel = self.qlabels[qidx - 1]
            for v in range(1, self.numberOfVersions + 1):
                _ = ProgressBox(self, qlabel, qidx, v)
                grid.addWidget(_, qidx, v)
                # keep ref so we can update it later in similar loop
                self.pd[(qidx, v)] = _
        self.ui.markBucket.setLayout(grid)
        self.refreshMarkTab()

    def refreshMarkTab(self):
        for q in range(1, self.numberOfQuestions + 1):
            for v in range(1, self.numberOfVersions + 1):
                stats = self.msgr.getProgress(q, v)
                self.pd[(q, v)].refresh(stats)

    def viewMarkHistogram(self, qlabel, qidx, version):
        mhist = self.msgr.getMarkHistogram(qidx, version)
        QVHistogram(self, qlabel, qidx, version, mhist).exec()

    def initOutTab(self):
        self.ui.tasksOutTW.setColumnCount(3)
        self.ui.tasksOutTW.setHorizontalHeaderLabels(["Task", "User", "Time (UTC)"])
        self.ui.tasksOutTW.setSortingEnabled(True)

    def refreshOutTab(self):
        tasksOut = self.msgr.RgetOutToDo()
        self.ui.tasksOutTW.clearContents()
        self.ui.tasksOutTW.setRowCount(0)

        if len(tasksOut) == 0:
            self.ui.tasksOutTW.setEnabled(False)
            return

        self.ui.tasksOutTW.setEnabled(True)
        self.ui.tasksOutTW.setSortingEnabled(False)
        for r, x in enumerate(tasksOut):
            self.ui.tasksOutTW.insertRow(r)
            k = 0
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, x[k])
            self.ui.tasksOutTW.setItem(r, k, item)
            k = 1
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, x[k])
            self.ui.tasksOutTW.setItem(r, k, item)
            k = 2  # the time - so set a tooltip too.
            time = arrow.get(x[k])
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, arrowtime_to_simple_string(time))
            item.setToolTip(time.humanize())
            self.ui.tasksOutTW.setItem(r, k, item)

        self.ui.tasksOutTW.setSortingEnabled(True)

    ##################
    # rubrics tab stuff

    def rubricsRefresh(self):
        r = self.msgr.MgetRubrics()
        # TODO fill a table
        self.ui.rubricsLabel.setText(f"Server has {len(r)} rubrics.")

    def rubricsDownload(self):
        WarnMsg(self, "Not implemented!").exec()

    rubricsUpload = rubricsDownload

    ##################
    # reassemble tab stuff

    def reassembleChooseFolder(self):
        dur = QFileDialog.getExistingDirectory(
            self,
            "Choose a directory for reassembling PDFs",
            None,
            QFileDialog.Option.ShowDirsOnly,
        )
        if dur == "":
            return
        dur = Path(dur)
        log.info("User explicitly chose %s for reassembling papers", dur)
        self.ui.reassembleFolderLineEdit.setText(str(dur))

    def reassemblePapers(self):
        from plom.finish import reassemble_paper, reassemble_all_papers

        # TODO: better to display progress bar, for now tqdm appears on stdout
        self.Qapp.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.Qapp.processEvents()

        where = Path(self.ui.reassembleFolderLineEdit.text())
        where.mkdir(exist_ok=True)
        where = where / "reassembled"
        testnum = self.ui.reassembleWhichSpinBox.value()
        if self.ui.radioButtonReassembleAll.isChecked():
            testnum = None
        skip_existing = True
        try:
            if testnum:
                reassemble_paper(
                    testnum, msgr=self.msgr, outdir=where, skip=skip_existing
                )
            else:
                reassemble_all_papers(msgr=self.msgr, outdir=where, skip=skip_existing)
        except Exception as e:
            # TODO: more specific!
            self.Qapp.restoreOverrideCursor()
            WarnMsg(
                self,
                "<p>Could not reassemble. The following error message was given:</p>",
                info=e,
                details=f"Working directory: {where}\nError type: {type(e)}",
            ).exec()
        self.Qapp.restoreOverrideCursor()
        self.setEnabled(True)

    def reassembleSolutions(self):
        from plom.finish import assemble_solutions

        # TODO: better to display progress bar, for now tqdm appears on stdout
        self.Qapp.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # disable ui before calling process events
        self.setEnabled(False)
        self.Qapp.processEvents()

        where = Path(self.ui.reassembleFolderLineEdit.text())
        where.mkdir(exist_ok=True)
        where = where / "solutions"
        testnum = self.ui.reassembleWhichSpinBox.value()
        if self.ui.radioButtonReassembleAll.isChecked():
            testnum = None
        try:
            assemble_solutions(
                testnum=testnum,
                msgr=self.msgr,
                outdir=where,
                watermark=False,
                verbose=True,
            )
        except Exception as e:
            # TODO: more specific!
            self.Qapp.restoreOverrideCursor()
            WarnMsg(
                self,
                "<p>Could not reassemble solution. The following error message was given:</p>",
                info=e,
                details=f"Working directory: {where}\nError type: {type(e)}",
            ).exec()
        self.Qapp.restoreOverrideCursor()
        self.setEnabled(True)

    ##################
    # review tab stuff

    def initReviewTab(self):
        self.initRevMTab()
        self.initRevIDTab()

    def initRevMTab(self):
        self.ui.reviewTW.setColumnCount(8)
        self.ui.reviewTW.setHorizontalHeaderLabels(
            [
                "Test",
                "Question index",
                "Version",
                "Mark",
                "Username",
                "Marking Time",
                "When",
                "Tags",
            ]
        )
        self.ui.reviewTW.setSortingEnabled(True)
        self.ui.reviewTW.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ui.reviewTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.reviewTW.activated.connect(self.reviewAnnotated)
        self.ui.viewAnnotationsButton.clicked.connect(self.reviewAnnotated)
        self.ui.changeTagsButton.clicked.connect(self.reviewChangeTags)

        # TODO: where to define this function?  Probably a method of a subclass of reviewTW
        def f(tw, i, row):
            """Insert the things from row into the ith row of the table tw."""
            N = 8
            assert len(row) == N
            assert tw.columnCount() == N
            # otherwise they resort between elements of the row (!)
            tw.setSortingEnabled(False)
            tw.insertRow(i)
            for k, x in enumerate(row):
                item = QTableWidgetItem()
                if k == 6:
                    # if we have a time value, use tooltip for humanised time
                    if x and x != "n/a":
                        time = arrow.get(x)
                        x = arrowtime_to_simple_string(time)
                        item.setToolTip(time.humanize())
                elif k == 7:
                    # flatten the tag list to a string
                    # TODO: possible to keep the list too, in some other Role?
                    x = ", ".join(x)
                # TODO: display question label, but other code expects qidx here
                # elif k == 1:
                #     x = self.qlabels[x - 1]
                item.setData(Qt.ItemDataRole.DisplayRole, x)
                tw.setItem(i, k, item)
            if row[4] == "reviewer":
                for k in range(N):
                    tw.item(i, k).setBackground(QBrush(QColor(0, 255, 0, 48)))
            if row[3] == "n/a":
                for k in range(N):
                    tw.item(i, k).setBackground(QBrush(QColor(255, 255, 128, 64)))
            tw.setSortingEnabled(True)

        # TODO: for now, monkey-patch the inserter into reviewTW
        # self.ui.reviewTW.__class__._fill_row_from = f
        self.ui.reviewTW._fill_row_from = f

        # maps zero to special text
        self.ui.reviewPaperNumSpinBox.setSpecialValueText("*")
        self.ui.reviewPaperNumSpinBox.setRange(0, self.max_papernum)

        self.ui.questionCB.addItem("*")
        for q in self.qlabels:
            self.ui.questionCB.addItem(q)
        self.ui.versionCB.addItem("*")
        for v in range(self.numberOfVersions):
            self.ui.versionCB.addItem(str(v + 1))
        self.ui.filterB.clicked.connect(self.filterReview)
        self.refreshMRev()

    def refreshMRev(self):
        """Refresh user list, tags, and any other server-dependent fields in marking review tab."""
        # clean out the combox box and then rebuild it.
        # TODO: bit annoying that these remove your selection: should we save that?
        self.ui.userCB.clear()
        ulist = self.msgr.getUserList()
        self.ui.userCB.addItem("*")
        for u in ulist:
            self.ui.userCB.addItem(u)
        # clean out the tag box and rebuild
        self.ui.tagsCB.clear()
        self.ui.tagsCB.addItem("*")
        self.ui.tagsCB.addItem("<1+ tags>")
        self.ui.tagsCB.addItem("<0 tags>")
        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        self.ui.tagsCB.addItems(all_tags)

    def filterReview(self):
        t0 = time()
        markedOnly = self.ui.markedOnlyCB.isChecked()
        # 1-based question indexing but 0th element is the any match
        qidx = self.ui.questionCB.currentIndex()
        if qidx == 0:
            qidx = "*"
        mrList = self.msgr.getMarkReview(
            filterPaperNumber=self.ui.reviewPaperNumSpinBox.text(),
            filterQ=qidx,
            filterV=self.ui.versionCB.currentText(),
            filterUser=self.ui.userCB.currentText(),
            filterMarked=markedOnly,
        )
        self.ui.reviewTW.clearContents()
        self.ui.reviewTW.setRowCount(0)
        # TODO: for some reason, doing tag filtering client side but is not obvious to user
        filter_tag = self.ui.tagsCB.currentText()
        r = 0
        t1 = time()
        for dat in mrList:
            # under various tagging conditions, we do *not* add this row
            if filter_tag == "*":
                pass
            elif filter_tag == "<1+ tags>":
                if len(dat[7]) == 0:
                    continue
            elif filter_tag == "<0 tags>":
                if len(dat[7]) != 0:
                    continue
            elif filter_tag not in dat[7]:
                continue
            self.ui.reviewTW._fill_row_from(self.ui.reviewTW, r, dat)
            r += 1
        t2 = time()
        log.debug("filterReview: %.3gs waiting for API call", t1 - t0)
        if t2 - t1 > 0.5:
            log.warning("filterReview: slow UI table build: %.3gs", t2 - t1)

    def reviewAnnotated(self):
        ri = self.ui.reviewTW.selectedIndexes()
        if len(ri) != self.ui.reviewTW.columnCount():
            # don't do anything unless we have exactly one row
            return
        r = ri[0].row()
        # no action if row is unmarked
        if self.ui.reviewTW.item(r, 3).text() == "n/a":
            # TODO - in future fire up reviewer with original pages
            return
        test = int(self.ui.reviewTW.item(r, 0).text())
        question = int(self.ui.reviewTW.item(r, 1).text())
        owner = self.ui.reviewTW.item(r, 4).text()
        img_info, img_bytes = self.msgr.get_annotations_image(test, question)
        ext = "." + img_info["extension"]
        # Context manager not appropriate, Issue #1996
        f = Path(tempfile.NamedTemporaryFile(delete=False, suffix=ext).name)
        with open(f, "wb") as fh:
            fh.write(img_bytes)
        qlabel = self.qlabels[question - 1]
        ReviewViewWindow(self, [f], stuff=(test, question, qlabel, owner)).exec()
        f.unlink()

    def reviewFlagTableRowsForReview(self):
        ri = self.ui.reviewTW.selectedIndexes()
        if len(ri) == 0:
            return
        # index is over rows and columns (yuck) so need some modular arithmetic
        mod = self.ui.reviewTW.columnCount()
        howmany = len(ri) // mod
        howmany = "1 question" if howmany == 1 else f"{howmany} questions"
        d = WarningQuestion(
            self,
            review_beta_warning,
            question=f"Are you sure you want to <b>flag {howmany}</b> for review?",
        )
        if not d.exec() == QMessageBox.StandardButton.Yes:
            return
        self.ui.reviewIDTW.setSortingEnabled(False)
        for tmp in ri[::mod]:
            r = tmp.row()
            # no action if row is unmarked
            if self.ui.reviewTW.item(r, 3).text() == "n/a":
                continue
            test = int(self.ui.reviewTW.item(r, 0).text())
            question = int(self.ui.reviewTW.item(r, 1).text())
            owner = self.ui.reviewTW.item(r, 4).text()
            self.flag_question_for_review(test, question, owner)
            # TODO: needs to be a method call to fix highlighting
            self.ui.reviewTW.item(r, 4).setText("reviewer")
        self.ui.reviewIDTW.setSortingEnabled(True)

    def flag_question_for_review(self, test, question, owner):
        # first remove auth from that user - safer.
        if owner != "reviewer":
            self.msgr.clearAuthorisationUser(owner)
        # then map that question's owner "reviewer"
        try:
            self.msgr.MreviewQuestion(test, question)
        except PlomConflict as e:
            s = "<p>You need to create a &ldquo;<tt>reviewer</tt>&rdquo; account"
            s += " before you can use this feature.</p>"
            InfoMsg(self, str(e), info=s, info_pre=False).exec()

    def removeAnnotationsFromRange(self):
        ri = self.ui.reviewTW.selectedIndexes()
        if len(ri) == 0:
            return
        # index is over rows and columns (yuck) so need some modular arithmetic
        mod = self.ui.reviewTW.columnCount()
        howmany = len(ri) // mod
        howmany = "1 question" if howmany == 1 else f"{howmany} questions"
        d = WarningQuestion(
            self,
            revert_beta_warning,
            question=f"Are you sure you want to <b>revert {howmany}</b>?",
        )
        if not d.exec() == QMessageBox.StandardButton.Yes:
            return
        self.ui.reviewIDTW.setSortingEnabled(False)
        for tmp in ri[::mod]:
            r = tmp.row()
            # no action if row is unmarked
            if self.ui.reviewTW.item(r, 3).text() == "n/a":
                continue
            test = int(self.ui.reviewTW.item(r, 0).text())
            question = int(self.ui.reviewTW.item(r, 1).text())
            self.remove_annotations_from_task(test, question)
            # TODO: needs to be a method call to fix highlighting
        self.ui.reviewIDTW.setSortingEnabled(True)
        rf = SimpleQuestion(
            self,
            "The data in the table is now outdated.",
            question="Do you want to refresh the table?",
        )
        if not rf.exec() == QMessageBox.StandardButton.Yes:
            return
        self.filterReview()

    def remove_annotations_from_task(self, test, question):
        task = f"q{test:04}g{question}"
        self.msgr.MrevertTask(task)

    def reviewChangeTags(self):
        ri = self.ui.reviewTW.selectedIndexes()
        if len(ri) == 0:
            return
        mod = self.ui.reviewTW.columnCount()
        howmany = len(ri) // mod
        howmany = "1 question" if howmany == 1 else f"{howmany} questions"
        self.ui.reviewIDTW.setSortingEnabled(False)
        # TODO: this loop is expensive when many rows highlighted
        # TODO: maybe just use the 7th column instead of talking to server
        tags = set()
        for tmp in ri[::mod]:
            r = tmp.row()
            paper = int(self.ui.reviewTW.item(r, 0).text())
            question = int(self.ui.reviewTW.item(r, 1).text())
            task = f"q{paper:04}g{question}"
            tags.update(self.msgr.get_tags(task))
        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        tag_choices = [X for X in all_tags if X not in tags]
        artd = AddRemoveTagDialog(self, tags, tag_choices, label=howmany)
        if artd.exec() != QDialog.DialogCode.Accepted:
            return
        cmd, new_tag = artd.return_values
        if cmd == "add":
            if new_tag:
                try:
                    for tmp in ri[::mod]:
                        r = tmp.row()
                        paper = int(self.ui.reviewTW.item(r, 0).text())
                        question = int(self.ui.reviewTW.item(r, 1).text())
                        task = f"q{paper:04}g{question}"
                        log.debug('%s: tagging "%s"', task, new_tag)
                        self.msgr.add_single_tag(task, new_tag)
                except PlomBadTagError as e:
                    errmsg = html.escape(str(e))
                    WarnMsg(self, "Tag not acceptable", info=errmsg).exec()
        elif cmd == "remove":
            for tmp in ri[::mod]:
                r = tmp.row()
                paper = int(self.ui.reviewTW.item(r, 0).text())
                question = int(self.ui.reviewTW.item(r, 1).text())
                task = f"q{paper:04}g{question}"
                log.debug('%s: removing tag "%s"', task, new_tag)
                try:
                    self.msgr.remove_single_tag(task, new_tag)
                except PlomConflict as e:
                    InfoMsg(
                        self,
                        "Tag was not present, perhaps someone else removed it?",
                        info=html.escape(str(e)),
                    ).exec()
        else:
            # do nothing - but shouldn't arrive here.
            pass

        # update the relevant table fields
        for tmp in ri[::mod]:
            r = tmp.row()
            paper = int(self.ui.reviewTW.item(r, 0).text())
            question = int(self.ui.reviewTW.item(r, 1).text())
            task = f"q{paper:04}g{question}"
            tags = self.msgr.get_tags(task)
            self.ui.reviewTW.item(r, 7).setData(
                Qt.ItemDataRole.DisplayRole, ", ".join(tags)
            )
        self.ui.reviewIDTW.setSortingEnabled(True)

    def manage_task_tags(self, paper_num, question, parent=None):
        """Manage the tags of a task.

        Args:
            paper_num (int/str): paper number.
            question (int/str): question idex.

        Keyword Args:
            parent (Window/None): Which window should be dialog's parent?
                If None, then use `self` (which is Marker) but if other
                windows (such as Annotator or PageRearranger) are calling
                this and if so they should pass themselves: that way they
                would be the visual parents of this dialog.

        Returns:
            list: the current tags of paper/question.  Note even if the
            dialog is cancelled, this will be updated (as someone else
            could've changed tags).
        """
        if not parent:
            parent = self

        # ugh, "GQ" nonsense:
        task = f"q{paper_num:04}g{question}"
        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        tags = self.msgr.get_tags(task)
        tag_choices = [X for X in all_tags if X not in tags]
        artd = AddRemoveTagDialog(self, tags, tag_choices, label=task)
        if artd.exec() == QDialog.DialogCode.Accepted:
            cmd, new_tag = artd.return_values
            if cmd == "add":
                if new_tag:
                    try:
                        log.debug('%s: tagging "%s"', task, new_tag)
                        self.msgr.add_single_tag(task, new_tag)
                    except PlomBadTagError as e:
                        errmsg = html.escape(str(e))
                        WarnMsg(self, "Tag not acceptable", info=errmsg).exec()
            elif cmd == "remove":
                log.debug('%s: removing tag "%s"', task, new_tag)
                try:
                    self.msgr.remove_single_tag(task, new_tag)
                except PlomConflict as e:
                    InfoMsg(
                        self,
                        "Tag was not present, perhaps someone else removed it?",
                        info=html.escape(str(e)),
                    ).exec()
            else:
                # do nothing - but shouldn't arrive here.
                pass

        current_tags = self.msgr.get_tags(task)
        return current_tags

    def initRevIDTab(self):
        self.ui.reviewIDTW.setColumnCount(5)
        self.ui.reviewIDTW.setHorizontalHeaderLabels(
            ["Test", "Username", "When", "Student ID", "Student Name"]
        )
        self.ui.reviewIDTW.setSortingEnabled(True)
        self.ui.reviewIDTW.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.ui.reviewIDTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.ui.reviewIDTW.activated.connect(self.reviewIDd)

        # monkey-patch in a row-insert routine
        def f(tw, i, row):
            """Insert data from row into the ith row of this table."""
            assert len(row) == 5
            # otherwise they resort during the insert, between elements!
            tw.setSortingEnabled(False)
            for k, x in enumerate(row):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, x)
                tw.setItem(i, k, item)
            if row[1] == "reviewer":
                for k in range(5):
                    tw.item(i, k).setBackground(QBrush(QColor(0, 255, 0, 48)))
            elif row[1] == "automatic":
                for k in range(5):
                    tw.item(i, k).setBackground(QBrush(QColor(0, 255, 255, 48)))
            tw.setSortingEnabled(True)

        # self.ui.reviewIDTW.__class__._fill_row_from = f
        self.ui.reviewIDTW._fill_row_from = f

    def refreshIDRev(self):
        irList = self.msgr.getIDReview()
        self.ui.reviewIDTW.clearContents()
        self.ui.reviewIDTW.setRowCount(0)
        for r, row_data in enumerate(irList):
            self.ui.reviewIDTW.insertRow(r)
            self.ui.reviewIDTW._fill_row_from(self.ui.reviewIDTW, r, row_data)

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
                ).exec()
                != QMessageBox.StandardButton.Yes
            ):
                return

        test = int(self.ui.reviewIDTW.item(r, 0).text())

        with tempfile.TemporaryDirectory() as td:
            pagedata = self.msgr.get_pagedata(test)
            id_pages = []
            for row in pagedata:
                # Issue #2707: better use a image-type key
                if not row["pagename"].casefold().startswith("id"):
                    continue
                img_bytes = self.msgr.get_image(row["id"], row["md5"])
                ext = Path(row["server_path"]).suffix
                filename = Path(td) / f'img_{int(test):04}_{row["pagename"]}{ext}'
                with open(filename, "wb") as fh:
                    fh.write(img_bytes)
                id_pages.append(filename)
            if not id_pages:
                return
            assert len(id_pages) == 1, "Expected at most one ID page"
            (img_name,) = id_pages

            rvw = ReviewViewWindowID(self, img_name)
            if rvw.exec() == QDialog.DialogCode.Accepted:
                # first remove auth from that user - safer.
                if self.ui.reviewIDTW.item(r, 1).text() != "reviewer":
                    self.msgr.clearAuthorisationUser(
                        self.ui.reviewIDTW.item(r, 1).text()
                    )
                # then map that question's owner "reviewer"
                # TODO: needs to be a method call to fix highlighting
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
                "Are you sure that you want to delete solution to"
                f" question index {self.ui.solnQSB.value()}"
                f" version {self.ui.solnVSB.value()}.",
            ).exec()
            == QMessageBox.StandardButton.Yes
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
                "Last activity (UTC)",
                "Last action",
                "Papers IDd",
                "Questions Marked",
            ]
        )
        self.ui.userListTW.setSortingEnabled(True)
        self.ui.userListTW.resizeColumnsToContents()
        self.ui.userListTW.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.ui.userListTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

    def initProgressQUTabs(self):
        self.ui.QPUserTW.setColumnCount(5)
        self.ui.QPUserTW.setHeaderLabels(
            [
                "Question index",
                "Version",
                "User",
                "Number Marked",
                "Avg time per task",
                "Percentage of Q/V marked",
            ]
        )
        # self.ui.QPUserTW.setSortingEnabled(True)
        self.ui.QPUserTW.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.ui.QPUserTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        # and the other tab
        self.ui.PUQTW.setColumnCount(5)
        self.ui.PUQTW.setHeaderLabels(
            [
                "User",
                "Question index",
                "Version",
                "Number Marked",
                "Avg time per task",
                "Percentage of Q/V marked",
            ]
        )
        # self.ui.PUQTW.setSortingEnabled(True)
        self.ui.PUQTW.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ui.PUQTW.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

    def forceLogout(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return

        selectedUsers = [self.ui.userListTW.item(i.row(), 0).text() for i in ri[::7]]

        if "manager" in selectedUsers:
            WarnMsg(
                self,
                "You cannot force-logout the manager. To logout, click on the Quit button.",
            ).exec()
            return
        # do something about this formatting? right now it's just a python list
        if (
            SimpleQuestion(
                self,
                "Are you sure you want to force-logout users {}?".format(selectedUsers),
            ).exec()
            == QMessageBox.StandardButton.Yes
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
                WarnMsg(self, str(e)).exec()
        self.refreshUserList()

    def disableUsers(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return

        selectedUsers = [self.ui.userListTW.item(i.row(), 0).text() for i in ri[::7]]

        msg = "Are you sure you want to disable "
        msg += "users " if len(selectedUsers) > 1 else "user "
        msg += ", ".join(f'"{x}"' for x in selectedUsers)
        if SimpleQuestion(self, msg).exec() != QMessageBox.StandardButton.Yes:
            return
        for user in selectedUsers:
            try:
                self.msgr.disableUser(user)
            except PlomConflict as e:
                WarnMsg(self, str(e)).exec()
        self.refreshUserList()

    def changeUserPassword(self):
        ri = self.ui.userListTW.selectedIndexes()
        if len(ri) == 0:
            return
        if len(ri) > 7:
            WarnMsg(
                self, "You can only change the password of one user at a time."
            ).exec()
            return

        r = ri[0].row()
        user = self.ui.userListTW.item(r, 0).text()
        cpwd = UserDialog(self, f'Change password for "{user}"', name=user)
        if cpwd.exec() == QDialog.DialogCode.Accepted:
            rval = self.msgr.changeUserPassword(user, cpwd.password)
            InfoMsg(self, rval[1]).exec()
        return

    def createUser(self):
        cpwd = UserDialog(self, "Create new user", name=None)
        if cpwd.exec() == QDialog.DialogCode.Accepted:
            rval = self.msgr.createUser(cpwd.name, cpwd.password)
            InfoMsg(self, rval[1]).exec()
            self.refreshUserList()
        return

    def refreshUserList(self):
        uDict = self.msgr.getUserDetails()
        self.ui.userListTW.clearContents()
        self.ui.userListTW.setRowCount(0)
        self.ui.userListTW.setSortingEnabled(False)
        for r, (u, dat) in enumerate(uDict.items()):
            self.ui.userListTW.insertRow(r)
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, u)
            if u in ["manager", "scanner", "reviewer"]:
                item.setBackground(QBrush(QColor(0, 255, 0, 48)))
            self.ui.userListTW.setItem(r, 0, item)

            k = 0
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, dat[k])
            if not dat[k]:
                item.setBackground(QBrush(QColor(255, 0, 0, 48)))
            self.ui.userListTW.setItem(r, k + 1, item)

            k = 1
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, dat[k])
            if dat[k]:
                item.setBackground(QBrush(QColor(0, 255, 0, 48)))
            self.ui.userListTW.setItem(r, k + 1, item)

            k = 2
            # change the last activity to be human readable
            time = arrow.get(dat[k])
            time.humanize()
            item = QTableWidgetItem()
            # TODO: want human-readable w/ raw tooltip but breaks sorting
            item.setData(Qt.ItemDataRole.DisplayRole, arrowtime_to_simple_string(time))
            item.setToolTip(time.humanize())
            self.ui.userListTW.setItem(r, k + 1, item)

            for k in range(3, 6):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, dat[k])
                self.ui.userListTW.setItem(r, k + 1, item)
        self.ui.userListTW.setSortingEnabled(True)

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
                for u, n, t in qpu[1:]:
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
