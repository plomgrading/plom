# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Forest Kobayashi
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2024 Bryan Tanady

"""Plom's Chooser dialog."""

from __future__ import annotations

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import logging
import re
import sys
import tempfile
import time
from typing import Any

import arrow
from packaging.version import Version
import platformdirs

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

import urllib3
from PyQt6 import uic, QtGui
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QMessageBox

from plom import __version__
from plom import Plom_API_Version
from plom import Default_Port
import plom.client.ui_files
from plom import get_question_label
from plom.plom_exceptions import (
    PlomException,
    PlomSeriousException,
    PlomBenignException,
    PlomAPIException,
    PlomAuthenticationException,
    PlomExistingLoginException,
    PlomServerNotReady,
    PlomSSLError,
    PlomNoServerSupportException,
)
from plom.messenger import Messenger, ManagerMessenger
from plom.client import MarkerClient, IDClient
from .downloader import Downloader
from .about_dialog import show_about_dialog
from .useful_classes import ErrorMsg, WarnMsg, InfoMsg, WarningQuestion
from .useful_classes import ClientSettingsDialog


log = logging.getLogger("client")
logdir = platformdirs.user_log_path("plom", "PlomGrading.org")
cfgdir = platformdirs.user_config_path("plom", "PlomGrading.org")
cfgfile = cfgdir / "plomConfig.toml"


def readLastTime() -> dict[str, Any]:
    """Read the login + server options that were used on the last run of the client."""
    lastTime: dict[str, Any] = {}
    # set some reasonable defaults.
    lastTime["LogToFile"] = True  # default until stable release?
    lastTime["user"] = ""
    lastTime["server"] = ""
    lastTime["question"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["KeyBinding"] = "default"
    # update default from config file
    if cfgfile.exists():
        # too early to log: log.info("Loading config file %s", cfgfile)
        with open(cfgfile, "rb") as f:
            lastTime.update(tomllib.load(f))
    return lastTime


class Chooser(QDialog):
    def __init__(self, Qapp):
        self.APIVersion = Plom_API_Version
        super().__init__()
        uic.loadUi(resources.files(plom.client.ui_files) / "chooser.ui", self)
        self.Qapp = Qapp
        self.messenger = None
        self._old_client_note_seen = False

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

        # TODO: with uic, we don't have a .ui: can go through and remove
        self.ui = self

        self.mportSB.setValue(int(Default_Port))
        # Append version to window title
        self.setWindowTitle("{} {}".format(self.windowTitle(), __version__))
        self.ui.markButton.clicked.connect(self.run_marker)
        self.ui.identifyButton.clicked.connect(self.run_identifier)
        self.ui.aboutButton.clicked.connect(lambda: show_about_dialog(self))
        # Hide button used for directly opening manager
        self.ui.manageButton.setVisible(False)
        self.ui.manageButton.clicked.connect(self.run_manager)
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.fontSB.valueChanged.connect(self.setFontSize)
        self.ui.optionsButton.clicked.connect(self.options)
        self.ui.getServerInfoButton.clicked.connect(self.validate_server)
        self.ui.logoutButton.setVisible(False)
        self.ui.logoutButton.clicked.connect(self.logout)
        # Chooser is a QDialog and has special Enter behaviour
        # TODO: but it doesn't work, Issue #3423.
        self.ui.loginButton.setDefault(True)
        self.ui.loginButton.clicked.connect(self.login)
        # clear the validation on server edit
        self.ui.serverLE.textEdited.connect(self.ungetInfo)
        self.ui.serverLE.setPlaceholderText("plom.example.com")
        self.ui.mportSB.valueChanged.connect(self.ungetInfo)
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.setVisible(False)

        # TODO: properly with a QValidator? maybe as part of a more general parser
        self.ui.serverLE.editingFinished.connect(self.partial_parse_address)

        # set login etc from last time client ran.
        self.ui.userLE.setText(self.lastTime["user"])
        self.setServer(self.lastTime["server"])
        self.ui.pgSB.setMinimum(1)
        self.ui.vSB.setMinimum(1)
        self.ui.pgSB.setValue(int(self.lastTime["question"]))
        self.ui.vSB.setValue(int(self.lastTime["v"]))
        self.ui.fontSB.setValue(int(self.lastTime["fontSize"]))

    # TODO: see Issue #3423, this below workaround doesn't work for me
    # def keyPressEvent(self, event):
    #     if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
    #         # Only connect to login if the current focus is at password line edit
    #         # Otherwise the return key works as default.
    #         if self.focusWidget() == self.ui.passwordLE:
    #             self.login()
    #         else:
    #             super().keyPressEvent(event)

    def setServer(self, s: str) -> None:
        """Set the server and port UI widgets from a string.

        If port is missing, a default will be used.  If we cannot
        parse the url, just leave it alone.
        """
        self.ui.serverLE.setText(s)
        self.partial_parse_address()

    def options(self) -> None:
        d = ClientSettingsDialog(
            self, self.lastTime, logdir, cfgfile, tempfile.gettempdir()
        )
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        # TODO: do something more proper like QSettings
        opt = d.get_options_back()
        self.lastTime["FOREGROUND"] = opt["FOREGROUND"]
        self.lastTime["LogLevel"] = opt["LogLevel"]
        self.lastTime["LogToFile"] = opt["LogToFile"]
        logging.getLogger().setLevel(self.lastTime["LogLevel"].upper())

    def launch_task(self, which_subapp: str) -> None:
        if not self.is_logged_in():
            self.login()
            if not self.is_logged_in():
                return

        assert self.messenger is not None
        if self.messenger.is_legacy_server() and self.messenger.username == "manager":
            if which_subapp != "Manager":
                InfoMsg(
                    self,
                    "<p>You are not allowed to mark or ID papers while "
                    "logged-in as &ldquo;manager&rdquo;.</p>",
                ).exec()
                return

        self.saveDetails()

        tmpdir = tempfile.mkdtemp(prefix="plom_local_img_")
        self.Qapp.downloader = Downloader(tmpdir, msgr=self.messenger)
        try:
            role = self.messenger.get_user_role()
        except PlomNoServerSupportException:
            role = ""

        if which_subapp == "Manager":
            if not self.messenger.is_legacy_server():
                InfoMsg(
                    self,
                    "<p>Only legacy servers have a manager app: "
                    "how did you get here?</p>",
                ).exec()
                return
            if not self.messenger.username == "manager":
                InfoMsg(self, 'Only "manager" can manager.').exec()
                return

            # Importing here avoids a circular import
            from plom.manager import Manager

            self.setEnabled(False)
            self.hide()
            window = Manager(self.Qapp, manager_msgr=self.messenger)
            window.show()
            # store ref in Qapp to avoid garbase collection
            self.Qapp._manager_window = window
        elif which_subapp == "Marker":
            if len(role) and role not in ["marker", "lead_marker"]:
                WarnMsg(self, "Only marker/lead marker can mark papers!").exec()
                return
            question = self.getQuestion()
            v = self.getv()
            assert question is not None
            assert v is not None
            self.setEnabled(False)
            self.hide()
            markerwin = MarkerClient(self.Qapp)
            markerwin.my_shutdown_signal.connect(self.on_marker_window_close)
            markerwin.show()
            markerwin.setup(self.messenger, question, v, self.lastTime)
            # store ref in Qapp to avoid garbase collection
            self.Qapp.marker = markerwin
        elif which_subapp == "Identifier":
            if len(role) and role != "lead_marker":
                WarnMsg(self, "Only lead marker can identify papers!").exec()
                return
            self.setEnabled(False)
            self.hide()
            idwin = IDClient(self.Qapp)
            idwin.my_shutdown_signal.connect(self.on_identify_window_close)
            idwin.show()
            idwin.setup(self.messenger)
            # store ref in Qapp to avoid garbase collection
            self.Qapp.identifier = idwin
        else:
            raise RuntimeError("Invalid subapplication value")

    def run_marker(self) -> None:
        self.launch_task("Marker")

    def run_identifier(self) -> None:
        self.launch_task("Identifier")

    def run_manager(self) -> None:
        self.launch_task("Manager")

    def saveDetails(self) -> None:
        """Write the options to the config file."""
        self.lastTime["user"] = self.ui.userLE.text().strip()
        server = self.ui.serverLE.text().strip()
        port_txt = self.ui.mportSB.text()
        if port_txt:
            server += ":" + port_txt
        self.lastTime["server"] = server
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

    def closeEvent(self, event: None | QtGui.QCloseEvent) -> None:
        self.saveDetails()
        dl = getattr(self.Qapp, "downloader", None)
        if dl and dl.has_messenger():
            # TODO: do we just wait forever?
            # TODO: Marker already tried to stop it: maybe never get here?
            dl.stop(-1)
        self.logout()

    def setFontSize(self, n: int) -> None:
        """Adjust font size of user interface.

        Args:
            n: the desired font size in points.
        """
        fnt = self.Qapp.font()
        fnt.setPointSize(n)
        self.Qapp.setFont(fnt)

    def getQuestion(self) -> int | None:
        """Return the integer question or None."""
        if self.ui.pgDrop.isVisible():
            question = self.ui.pgDrop.currentIndex() + 1
        else:
            question = self.ui.pgSB.value()
        try:
            return int(question)
        except ValueError:
            return None

    def getv(self) -> int | None:
        """Return the integer version or None."""
        if self.ui.vDrop.isVisible():
            v = self.ui.vDrop.currentText()
        else:
            v = self.ui.vSB.value()
        try:
            return int(v)
        except:  # noqa: E722
            return None

    def ungetInfo(self) -> None:
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
        self.logout()

    def _pre_login_connection(self, msgr: Messenger | ManagerMessenger) -> bool:
        # This msgr object may or may not be logged in: it can be temporary: we
        # only use it to get public info from the server.
        #
        # Side effects:
        #    The `msgr` itself will be modified, e.g., if user excepted
        #    SSL verification.   It also figures out if we're talking to
        #    a legacy or new server (and stores that info).
        _ssl_excused = False
        try:
            try:
                server_ver_str = msgr._start()
            except PlomSSLError as e:
                msg = WarningQuestion(
                    self,
                    "SSL error: cannot verify the identity of the server.",
                    "Do you want to disable SSL certificate verification?  Not recommended.",
                    details=f"{e}",
                )
                msg.setDefaultButton(QMessageBox.StandardButton.No)
                if msg.exec() == QMessageBox.StandardButton.No:
                    return False
                _ssl_excused = True
                msgr.force_ssl_unverified()
                server_ver_str = msgr._start()
        except PlomBenignException as e:
            WarnMsg(
                self,
                f"<p>Could not connect to server &ldquo;{msgr.server}&rdquo;.<br />"
                "Check the server address and your internet connection?</p>"
                " <p>The precise error message was:</p>",
                info=f"{e}",
                info_pre=False,
            ).exec()
            return False

        try:
            (srv_ver,) = re.findall(r"Plom server version (\S+)", server_ver_str)
        except ValueError:
            self.ui.infoLabel.setText(
                "Unexpected response: " + server_ver_str.strip()[:15]
            )
            WarnMsg(
                self,
                "Unexpected server response on version query.",
                details=server_ver_str.strip(),
            ).exec()
            msgr.stop()
            return False
        self.ui.infoLabel.setText(server_ver_str)

        if _ssl_excused:
            s = "\nCaution: SSL exception granted."
            self.ui.infoLabel.setText(self.ui.infoLabel.text() + s)

        # in theory we could support older servers by scrapping the API version from above
        info = msgr.get_server_info()
        if "Legacy" in info["product_string"]:
            msgr.enable_legacy_server_support()
            s = "\nUsing legacy messenger"
            self.ui.infoLabel.setText(self.ui.infoLabel.text() + s)
        else:
            msgr.disable_legacy_server_support()

        if Version(__version__) < Version(srv_ver):
            s = "\nWARNING: old client!"
            self.ui.infoLabel.setText(self.ui.infoLabel.text() + s)
            msg = WarnMsg(
                self,
                f"Your client version {__version__} is older than the server {srv_ver}:"
                " you may want to consider upgrading.",
                details=(
                    f"You have Plom Client {__version__} with API {self.APIVersion}"
                    f"\nServer version string: “{server_ver_str}”\n"
                    f"Regex-extracted server version: {srv_ver}."
                ),
            )
            if not self._old_client_note_seen:
                msg.exec()
                self._old_client_note_seen = True
        return True

    def validate_server(self) -> None:
        self.start_messenger_get_info()
        if not self.messenger:
            return
        # if successful, put focus at username or password line-edit
        if len(self.ui.userLE.text()) > 0:
            self.ui.passwordLE.setFocus()
        else:
            self.ui.userLE.setFocus()

    def start_messenger_get_info(
        self, *, _legacy_username: str | None = None, verify_ssl: bool = True
    ) -> None:
        """Get info from server, update UI with server version, check SSL.

        Keyword Args:
            _legacy_username: normally we don't care who might eventually
                login, except in the legacy case and if it might be the
                manager.
            verify_ssl: True by default but if False then don't pop up
                dialogs about lacking SSL verification.  Should not be
                used lightly!  Currently we let users make this decision
                one login at a time.

        Returns:
            None, but modifies the state of the internal `messenger`
            instance variable.  If that is not None, you can assume
            something reasonable happened.
        """
        server = self.ui.serverLE.text().strip()
        if not server:
            self.ui.infoLabel.setText("You must specify a server address")
            return
        # due to special handling of blank versus default, use .text() not .value()
        port = self.ui.mportSB.text()

        # TODO: might be nice, but needs another thread?
        # self.ui.infoLabel.setText("connecting...")
        # self.ui.infoLabel.repaint()

        if self.is_logged_in():
            self.logout()
        if self.messenger:
            self.messenger.stop()
            self.messenger = None

        try:
            msgr: Messenger | ManagerMessenger = Messenger(
                server, port=port, verify_ssl=verify_ssl
            )
            if not self._pre_login_connection(msgr):
                return
        except PlomException as e:
            WarnMsg(self, "Could not connect to server", info=str(e)).exec()
            return

        if msgr.is_legacy_server():
            if _legacy_username and _legacy_username == "manager":
                verified = msgr.is_ssl_verified()
                msgr.stop()
                msgr = ManagerMessenger(server, port=port, verify_ssl=verified)
                if not self._pre_login_connection(msgr):
                    return

        # Once we're happy with the manager keep it, b/c it knows if we
        # have made an SSL exception for example.
        self.messenger = msgr

    def is_logged_in(self) -> bool:
        if not self.messenger:
            return False
        if self.messenger.token:
            return True
        return False

    def logout(self) -> None:
        """Logout if not already logged out.

        Its safe to call this if you're not logged in, don't have a messenger etc.
        """
        if not self.messenger:
            return
        try:
            self.messenger.closeUser()
        except PlomAuthenticationException as e:
            log.info(f"Authentication error during logout: {e}")
            pass
        self.messenger.stop()
        self.messenger = None
        self.ui.loginInfoLabel.setText("logged out")
        self._old_client_note_seen = False
        self.ui.manageButton.setVisible(False)
        self.ui.logoutButton.setVisible(False)
        self.ui.userLE.setEnabled(True)
        self.ui.passwordLE.setEnabled(True)
        self.ui.serverLE.setEnabled(True)
        self.ui.mportSB.setEnabled(True)
        self.ui.loginButton.setEnabled(True)

    def login(self) -> None:
        """Login to the server but don't start any tasks yet.

        Also update the UI with restricted questions and versions.
        """
        user = self.ui.userLE.text().strip()
        self.ui.userLE.setText(user)
        if not user:
            return
        pwd = self.ui.passwordLE.text()
        if not pwd:
            return

        if self.is_logged_in():
            self.logout()

        verified = True
        # Legacy special cases if we already have the wrong type of messenger,
        # e.g., someone changed the username after validating but before login.
        if self.messenger and self.messenger.is_legacy_server():
            if user == "manager" and not isinstance(self.messenger, ManagerMessenger):
                verified = self.messenger.is_ssl_verified()
                self.logout()
            elif user != "manager" and isinstance(self.messenger, ManagerMessenger):
                verified = self.messenger.is_ssl_verified()
                self.logout()

        if not self.messenger:
            self.start_messenger_get_info(_legacy_username=user, verify_ssl=verified)
            if not self.messenger:
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
            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.messenger.clearAuthorisation(user, pwd)
                # harmless probably useless pause, in case Issue #2328 was real
                time.sleep(0.25)
                # try again
                self.login()
                return
            self.messenger = None
            return

        except PlomSeriousException as e:
            ErrorMsg(
                self,
                f"Could not get authentication token.\n\nUnexpected error: {str(e)}",
            ).exec()
            self.messenger = None
            return

        try:
            spec = self.messenger.get_spec()
        except PlomServerNotReady as e:
            if not self.messenger.username == "manager":
                WarnMsg(
                    self,
                    "Server does not yet have a spec, nothing to mark. "
                    " Perhaps you want to login with the manager account to"
                    " configure the server.",
                    info=str(e),
                ).exec()
                self.messenger = None
                return
            spec = None
        except PlomException as e:
            WarnMsg(self, "Could not connect to server", info=str(e)).exec()
            self.messenger = None
            return
        if spec:
            self._set_restrictions_from_spec(spec)
        self.ui.loginInfoLabel.setText(f'logged in as "{user}"')
        self.ui.logoutButton.setVisible(True)
        self.ui.userLE.setEnabled(False)
        self.ui.passwordLE.setEnabled(False)
        self.ui.serverLE.setEnabled(False)
        self.ui.mportSB.setEnabled(False)
        self.ui.loginButton.setEnabled(False)

        if not self.messenger.webplom and self.messenger.username == "manager":
            self.ui.manageButton.setVisible(True)

    def _set_restrictions_from_spec(self, spec: dict[str, Any]) -> None:
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

    def _partial_parse_address_manual(self) -> None:
        address = self.ui.serverLE.text()
        try:
            _addr, _port = address.split(":")
        except ValueError:
            return
        if _port == "":
            # special case handles "foo:"
            self.ui.serverLE.setText(_addr)
            return
        # this special case handles "foo:1234"
        try:
            _port = int(_port)
        except ValueError:
            # special case for stuff with path "foo:1234/user"
            self.ui.mportSB.clear()
            return
        self.ui.mportSB.setValue(_port)
        self.ui.serverLE.setText(_addr)

    def partial_parse_address(self) -> None:
        """If address has a port number in it, extract and move to the port box.

        If there's a colon in the address (maybe user did not see port
        entry box or is pasting in a string), then try to extract a port
        number and put it into the entry box.

        In some rare cases, we actively clear the port box, for example
        when the URL seems to have a path.
        """
        address = self.ui.serverLE.text()
        self.ui.mportSB.setEnabled(True)
        try:
            parsedurl = urllib3.util.parse_url(address)
            if not parsedurl.host:
                self._partial_parse_address_manual()
                return
            if parsedurl.scheme and parsedurl.scheme.casefold() != "https":
                # special case non-https uri
                self.ui.mportSB.clear()
                self.ui.mportSB.setEnabled(False)
                return
            if parsedurl.path:
                # don't muck with things like "localhost:1234/base/url"
                # activitely remove our port setting from such things
                self.ui.mportSB.clear()
                self.ui.mportSB.setEnabled(False)
                return
            if parsedurl.port:
                self.ui.mportSB.setValue(int(parsedurl.port))
                self.ui.serverLE.setText(parsedurl.host)
        except urllib3.exceptions.LocationParseError:
            return

    @pyqtSlot(int)
    def on_identify_window_close(self, value: int) -> None:
        # `value` is always 1, no real meaning yet
        self.show()
        self.setEnabled(True)
        # TODO: wall-paper for Issue #2903
        if not self.is_logged_in():
            self.logout()

    @pyqtSlot(int, list)
    def on_marker_window_close(self, value: int, stuff: list[Any] | None) -> None:
        # `value` is always 2, no real meaning yet
        self.show()
        self.setEnabled(True)
        # TODO: wall-paper for Issue #2903
        if not self.is_logged_in():
            self.logout()
        if not stuff:
            return
        # note `stuff` is list of options - used to contain more... may contain more in future
        # TODO: don't save custom until Issue #2254
        if stuff[0] != "custom":
            self.lastTime["KeyBinding"] = stuff[0]
        # TODO: not writing to disc until Issue #2254
        # self.lastTime["CustomKeys"] = stuff[1]
