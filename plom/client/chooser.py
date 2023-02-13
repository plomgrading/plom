# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Forest Kobayashi
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2022 Edith Coates

"""Chooser dialog"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import logging
from pathlib import Path
import sys
import tempfile
import time

import appdirs
import arrow
from packaging.version import Version

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

import urllib3
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QMessageBox

from plom import __version__
from plom import Plom_API_Version
from plom import Default_Port
from plom import get_question_label
from plom.plom_exceptions import (
    PlomException,
    PlomSeriousException,
    PlomBenignException,
    PlomAPIException,
    PlomAuthenticationException,
    PlomExistingLoginException,
    PlomSSLError,
)
from plom.messenger import Messenger, ManagerMessenger
from plom.client import MarkerClient, IDClient
from .downloader import Downloader
from .about_dialog import show_about_dialog
from .uiFiles.ui_chooser import Ui_Chooser
from .useful_classes import ErrorMsg, WarnMsg, InfoMsg, SimpleQuestion, WarningQuestion
from .useful_classes import ClientSettingsDialog


log = logging.getLogger("client")
logdir = Path(appdirs.user_log_dir("plom", "PlomGrading.org"))
cfgdir = Path(appdirs.user_config_dir("plom", "PlomGrading.org"))
cfgfile = cfgdir / "plomConfig.toml"


def readLastTime():
    """Read the login + server options that were used on
    the last run of the client.
    """
    lastTime = {}
    # set some reasonable defaults.
    lastTime["LogToFile"] = True  # default until stable release?
    lastTime["user"] = ""
    lastTime["server"] = "localhost"
    lastTime["question"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["CommentsWarnings"] = True
    lastTime["MarkWarnings"] = True
    lastTime["KeyBinding"] = "default"
    # update default from config file
    if cfgfile.exists():
        # too early to log: log.info("Loading config file %s", cfgfile)
        with open(cfgfile, "rb") as f:
            lastTime.update(tomllib.load(f))
    return lastTime


class Chooser(QDialog):
    def __init__(self, Qapp, webplom=False):
        self.APIVersion = Plom_API_Version
        super().__init__()
        self.Qapp = Qapp
        self.messenger = None
        self.webplom = webplom

        self.lastTime = readLastTime()

        kwargs = {}
        if self.lastTime.get("LogToFile"):
            # filename must not have ":" (forbidden on win32)
            # e.g., use "ZZZ" not "ZZ" as the latter has "+00:00"
            now = arrow.now().format("YYYY-MM-DD_HH-mm-ss_ZZZ")
            logfile = f"plomclient-{now}.log"
            try:
                logdir.mkdir(parents=True, exist_ok=True)
                logfile = logdir / logfile
            except PermissionError:
                pass
            kwargs = {"filename": logfile}
        logging.basicConfig(
            format="%(asctime)s %(levelname)5s:%(name)s\t%(message)s",
            datefmt="%b%d %H:%M:%S %Z",
            **kwargs,
        )
        # Default to INFO log level
        logging.getLogger().setLevel(self.lastTime.get("LogLevel", "Info").upper())

        s = "Plom Client {} (communicates with api {})".format(
            __version__, self.APIVersion
        )
        log.info(s)

        self.ui = Ui_Chooser()
        self.ui.setupUi(self)
        # Append version to window title
        self.setWindowTitle("{} {}".format(self.windowTitle(), __version__))
        self.ui.markButton.clicked.connect(self.run_marker)
        self.ui.identifyButton.clicked.connect(self.run_identifier)
        self.ui.aboutButton.clicked.connect(lambda: show_about_dialog(self))
        # Hide button used for directly opening manager
        # self.ui.manageButton.clicked.connect(self.run_manager)
        self.ui.manageButton.setVisible(False)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.fontSB.valueChanged.connect(self.setFont)
        self.ui.optionsButton.clicked.connect(self.options)
        self.ui.getServerInfoButton.clicked.connect(self.getInfo)
        self.ui.serverLE.textEdited.connect(self.ungetInfo)
        self.ui.mportSB.valueChanged.connect(self.ungetInfo)
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.setVisible(False)

        # set login etc from last time client ran.
        self.ui.userLE.setText(self.lastTime["user"])
        self.setServer(self.lastTime["server"])
        self.ui.pgSB.setMinimum(1)
        self.ui.vSB.setMinimum(1)
        self.ui.pgSB.setValue(int(self.lastTime["question"]))
        self.ui.vSB.setValue(int(self.lastTime["v"]))
        self.ui.fontSB.setValue(int(self.lastTime["fontSize"]))

    def setServer(self, s):
        """Set the server and port UI widgets from a string.

        If port is missing, a default will be used."""
        try:
            s, p = s.split(":")
        except ValueError:
            p = Default_Port
        self.ui.serverLE.setText(s)
        self.ui.mportSB.setValue(int(p))

    def options(self):
        d = ClientSettingsDialog(
            self, self.lastTime, logdir, cfgfile, tempfile.gettempdir()
        )
        d.exec()
        # TODO: do something more proper like QSettings
        stuff = d.getStuff()
        self.lastTime["FOREGROUND"] = stuff[0]
        self.lastTime["LogLevel"] = stuff[1]
        self.lastTime["LogToFile"] = stuff[2]
        self.lastTime["CommentsWarnings"] = stuff[3]
        self.lastTime["MarkWarnings"] = stuff[4]
        logging.getLogger().setLevel(self.lastTime["LogLevel"].upper())

    def validate(self, which_subapp):
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
        if not server:
            log.warning("No server URI")
            return
        mport = self.ui.mportSB.value()

        self.saveDetails()

        if user == "manager":
            msg = SimpleQuestion(
                self,
                "<p>You are not allowed to mark or ID papers while logged-in as &ldquo;manager&rdquo;.</p>",
                "Would you instead like to run the Server Management tool?",
            )
            if msg.exec() == QMessageBox.No:
                return
            which_subapp = "Manager"
            self.messenger = None

        if not self.messenger:
            if which_subapp == "Manager":
                self.messenger = ManagerMessenger(server, mport, webplom=self.webplom)
            else:
                self.messenger = Messenger(server, mport, webplom=self.webplom)
        try:
            try:
                server_ver_str = self.messenger.start()
            except PlomSSLError as e:
                msg = WarningQuestion(
                    self,
                    "SSL error: cannot verify the identity of the server.",
                    "Do you want to disable SSL certificate verification?  Not recommended.",
                    details=f"{e}",
                )
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() == QMessageBox.No:
                    self.messenger = None
                    return
                self.messenger.force_ssl_unverified()
                server_ver_str = self.messenger.start()
        except PlomBenignException as e:
            WarnMsg(
                self, "Could not connect to server:", info=f"{e}", info_pre=False
            ).exec()
            self.messenger = None
            return

        try:
            self.messenger.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            WarnMsg(
                self,
                "Could not authenticate due to API mismatch.",
                info=f"Client version is {__version__}.  {e}",
                info_pre=False,
            ).exec()
            self.messenger = None
            return
        except PlomAuthenticationException as e:
            InfoMsg(self, f"Could not authenticate: {e}").exec()
            self.messenger = None
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
            if msg.exec() == QMessageBox.Yes:
                self.messenger.clearAuthorisation(user, pwd)
                # harmless probably useless pause, in case Issue #2328 was real
                time.sleep(0.25)
                # try again
                self.validate(which_subapp)
                return
            self.messenger = None
            return

        except PlomSeriousException as e:
            ErrorMsg(
                self,
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e),
            ).exec()
            self.messenger = None
            return

        # fragile, use a regex?
        srv_ver = server_ver_str.split()[3]
        if Version(__version__) < Version(srv_ver):
            msg = WarningQuestion(
                self,
                f"Your client version {__version__} is older than the server {srv_ver}:"
                " you may want to consider upgrading.",
                question="Do you want to continue?",
                details=(
                    f"You have Plom Client {__version__} with API {self.APIVersion}"
                    f"\nServer version string: “{server_ver_str}”\n"
                    f"Regex-extracted server version: {srv_ver}."
                ),
            )
            if msg.exec() != QMessageBox.Yes:
                self.messenger.closeUser()
                self.messenger.stop()
                self.messenger = None
                return

        tmpdir = tempfile.mkdtemp(prefix="plom_local_img_")
        self.Qapp.downloader = Downloader(tmpdir, msgr=self.messenger)

        if which_subapp == "Manager":
            # Importing here avoids a circular import
            from plom.manager import Manager

            self.setEnabled(False)
            self.hide()
            window = Manager(
                self.Qapp,
                manager_msgr=self.messenger,
                server=server,
                user=user,
                password=pwd,
            )
            window.show()
            # store ref in Qapp to avoid garbase collection
            self.Qapp._manager_window = window
        elif which_subapp == "Marker":
            question = self.getQuestion()
            v = self.getv()
            self.setEnabled(False)
            self.hide()
            markerwin = MarkerClient(self.Qapp)
            markerwin.my_shutdown_signal.connect(self.on_marker_window_close)
            markerwin.show()
            markerwin.setup(self.messenger, question, v, self.lastTime)
            # store ref in Qapp to avoid garbase collection
            self.Qapp.marker = markerwin
        elif which_subapp == "Identifier":
            self.setEnabled(False)
            self.hide()
            idwin = IDClient(self.Qapp)
            idwin.my_shutdown_signal.connect(self.on_other_window_close)
            idwin.show()
            idwin.setup(self.messenger)
            # store ref in Qapp to avoid garbase collection
            self.Qapp.identifier = idwin
        else:
            raise RuntimeError("Invalid subapplication value")

    def run_marker(self):
        self.validate("Marker")

    def run_identifier(self):
        self.validate("Identifier")

    def run_manager(self):
        self.validate("Manager")

    def saveDetails(self):
        """Write the options to the config file."""
        self.lastTime["user"] = self.ui.userLE.text().strip()
        self.lastTime["server"] = "{}:{}".format(
            self.ui.serverLE.text().strip(), self.ui.mportSB.value()
        )
        self.lastTime["question"] = self.getQuestion()
        self.lastTime["v"] = self.getv()
        self.lastTime["fontSize"] = self.ui.fontSB.value()
        log.info("Saving config file %s", cfgfile)
        try:
            cfgfile.parent.mkdir(exist_ok=True)
            with open(cfgfile, "w") as fh:
                tomlkit.dump(self.lastTime, fh)
        except OSError as e:
            WarnMsg(
                self,
                "Cannot write config file:\n"
                "    {}\n\n"
                "Any settings will not be saved for future sessions.\n\n"
                "Error msg: {}.".format(cfgfile, e),
            ).exec()

    def closeEvent(self, event):
        self.saveDetails()
        dl = getattr(self.Qapp, "downloader", None)
        if dl and dl.has_messenger():
            # TODO: do we just wait forever?
            # TODO: Marker already tried to stop it: maybe never get here?
            dl.stop(-1)
        if self.messenger:
            self.messenger.stop()

    def setFont(self, n):
        """Adjust font size of user interface.

        args:
            n (int): the desired font size in points.
        """
        fnt = self.Qapp.font()
        fnt.setPointSize(n)
        self.Qapp.setFont(fnt)

    def getQuestion(self):
        """Return the integer question or None"""
        if self.ui.pgDrop.isVisible():
            question = self.ui.pgDrop.currentIndex() + 1
        else:
            question = self.ui.pgSB.value()
        try:
            return int(question)
        except ValueError:
            return None

    def getv(self):
        """Return the integer version or None"""
        if self.ui.vDrop.isVisible():
            v = self.ui.vDrop.currentText()
        else:
            v = self.ui.vSB.value()
        try:
            return int(v)
        except:  # noqa: E722
            return None

    def ungetInfo(self):
        self.ui.markGBox.setTitle("Choose a task")
        question = self.getQuestion()
        v = self.getv()
        self.ui.pgSB.setVisible(True)
        self.ui.vSB.setVisible(True)
        if question:
            self.ui.pgSB.setValue(question)
        if v:
            self.ui.vSB.setValue(v)
        self.ui.vDrop.clear()
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.clear()
        self.ui.pgDrop.setVisible(False)
        self.ui.infoLabel.setText("")
        if self.messenger:
            self.messenger.stop()
        self.messenger = None

    def getInfo(self):
        self.partial_parse_address()
        server = self.ui.serverLE.text()
        self.ui.serverLE.setText(server)
        if not server:
            log.warning("No server URI")
            return
        mport = self.ui.mportSB.value()

        # save those settings
        # self.saveDetails()   # TODO?

        # TODO: might be nice, but needs another thread?
        # self.ui.infoLabel.setText("connecting...")
        # self.ui.infoLabel.repaint()

        if not self.messenger:
            self.messenger = Messenger(server, mport, webplom=self.webplom)

        try:
            try:
                server_ver_str = self.messenger.start()
            except PlomSSLError as e:
                msg = WarningQuestion(
                    self,
                    "SSL error: cannot verify the identity of the server.",
                    "Do you want to disable SSL certificate verification?  Not recommended.",
                    details=f"{e}",
                )
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() == QMessageBox.No:
                    self.messenger = None
                    return
                self.messenger.force_ssl_unverified()
                server_ver_str = self.messenger.start()
        except PlomBenignException as e:
            WarnMsg(
                self, "Could not connect to server:", info=f"{e}", info_pre=False
            ).exec()
            self.messenger = None
            return
        self.ui.infoLabel.setText(server_ver_str)

        # fragile, use a regex?
        srv_ver = server_ver_str.split()[3]
        if Version(__version__) < Version(srv_ver):
            self.ui.infoLabel.setText(server_ver_str + "\nWARNING: old client!")
            WarnMsg(
                self,
                f"Your client version {__version__} is older than the server {srv_ver}:"
                " you may want to consider upgrading.",
                details=(
                    f"You have Plom Client {__version__} with API {self.APIVersion}"
                    f"\nServer version string: “{server_ver_str}”\n"
                    f"Regex-extracted server version: {srv_ver}."
                ),
            ).exec()

        try:
            spec = self.messenger.get_spec()
        except PlomException as e:
            WarnMsg(self, "Could not connect to server", info=str(e)).exec()
            self.messenger = None
            return

        self.ui.markGBox.setTitle("Choose a task for “{}”".format(spec["name"]))
        question = self.getQuestion()
        v = self.getv()
        self.ui.pgSB.setVisible(False)
        self.ui.vSB.setVisible(False)

        self.ui.vDrop.clear()
        self.ui.vDrop.addItems([str(x + 1) for x in range(0, spec["numberOfVersions"])])
        if v:
            if v >= 1 and v <= spec["numberOfVersions"]:
                self.ui.vDrop.setCurrentIndex(v - 1)
        self.ui.vDrop.setVisible(True)

        self.ui.pgDrop.clear()
        self.ui.pgDrop.addItems(
            [get_question_label(spec, n + 1) for n in range(spec["numberOfQuestions"])]
        )
        if question:
            if question >= 1 and question <= spec["numberOfQuestions"]:
                self.ui.pgDrop.setCurrentIndex(question - 1)
        self.ui.pgDrop.setVisible(True)
        # TODO should we also let people type in?
        self.ui.pgDrop.setEditable(False)
        self.ui.vDrop.setEditable(False)
        # put focus at username or password line-edit
        if len(self.ui.userLE.text()) > 0:
            self.ui.passwordLE.setFocus()
        else:
            self.ui.userLE.setFocus()

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
        # note `stuff` is list of options - used to contain more... may contain more in future
        # TODO: don't save custom until Issue #2254
        if stuff[0] != "custom":
            self.lastTime["KeyBinding"] = stuff[0]
        # TODO: not writing to disc until Issue #2254
        # self.lastTime["CustomKeys"] = stuff[1]
