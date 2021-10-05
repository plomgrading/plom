# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020 Forest Kobayashi
# Copyright (C) 2021 Peter Lee

"""Chooser dialog"""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from datetime import datetime
import logging
from pathlib import Path
import tempfile

import toml
import appdirs

import urllib3
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog, QMessageBox

from plom import __version__
from plom import Plom_API_Version
from plom import Default_Port
from plom import get_question_label
from plom.plom_exceptions import (
    PlomSeriousException,
    PlomBenignException,
    PlomAPIException,
    PlomAuthenticationException,
    PlomExistingLoginException,
)
from plom.messenger import Messenger
from plom.client import MarkerClient, IDClient
from .uiFiles.ui_chooser import Ui_Chooser
from .useful_classes import ErrorMessage, SimpleMessage, ClientSettingsDialog

from plom.messenger import ManagerMessenger


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
    lastTime["upDown"] = "up"
    lastTime["CommentsWarnings"] = True
    lastTime["MarkWarnings"] = True
    # update default from config file
    if cfgfile.exists():
        # too early to log: log.info("Loading config file %s", cfgfile)
        with open(cfgfile) as f:
            lastTime.update(toml.load(f))
    return lastTime


def writeLastTime(lastTime):
    """Write the options to the config file."""
    log.info("Saving config file %s", cfgfile)
    try:
        cfgfile.parent.mkdir(exist_ok=True)
        with open(cfgfile, "w") as fh:
            fh.write(toml.dumps(lastTime))
    except PermissionError as e:
        ErrorMessage(
            "Cannot write config file:\n"
            "    {}\n\n"
            "Any settings will not be saved for future sessions.\n\n"
            "Error msg: {}.".format(cfgfile, e)
        ).exec_()


class Chooser(QDialog):
    def __init__(self, Qapp):
        self.APIVersion = Plom_API_Version
        super().__init__()
        self.parent = Qapp
        self.messenger = None

        self.lastTime = readLastTime()

        kwargs = {}
        if self.lastTime.get("LogToFile"):
            logfile = datetime.now().strftime("plomclient-%Y%m%d_%H-%M-%S.log")
            try:
                logdir.mkdir(parents=True, exist_ok=True)
                logfile = logdir / logfile
            except PermissionError:
                pass
            kwargs = {"filename": logfile}
        logging.basicConfig(
            format="%(asctime)s %(levelname)5s:%(name)s\t%(message)s",
            datefmt="%b%d %H:%M:%S",
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
        # Hide button used for directly opening manager
        # self.ui.manageButton.clicked.connect(self.run_manager)
        self.ui.manageButton.setVisible(False)
        self.ui.closeButton.clicked.connect(self.closeWindow)
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
        d = ClientSettingsDialog(self.lastTime, logdir, cfgfile, tempfile.gettempdir())
        d.exec_()
        # TODO: do something more proper like QSettings
        stuff = d.getStuff()
        self.lastTime["FOREGROUND"] = stuff[0]
        self.lastTime["LogLevel"] = stuff[1]
        self.lastTime["LogToFile"] = stuff[2]
        self.lastTime["CommentsWarnings"] = stuff[3]
        self.lastTime["MarkWarnings"] = stuff[4]
        self.lastTime["SidebarOnRight"] = stuff[5]
        logging.getLogger().setLevel(self.lastTime["LogLevel"].upper())

    def validate(self, which_subapp):
        # Check username is a reasonable string
        user = self.ui.userLE.text().strip()
        self.ui.userLE.setText(user)
        if (not user.isalnum()) or (not user):
            return
        # Don't strip whitespace from passwords
        pwd = self.ui.passwordLE.text()
        if len(pwd) < 4:
            log.warning("Password too short")
            return

        self.partial_parse_address()
        server = self.ui.serverLE.text()
        self.ui.serverLE.setText(server)
        if not server:
            log.warning("No server URI")
            return
        mport = self.ui.mportSB.value()

        # save those settings
        self.saveDetails()

        if user == "manager":
            _ = """
                <p>You are not allowed to mark or ID papers while logged-in
                  as &ldquo;manager&rdquo;.</p>
                <p>Would you instead like to run the Server Management tool?</p>
            """
            if SimpleMessage(_).exec_() == QMessageBox.No:
                return
            which_subapp = "Manager"
            self.messenger = None

        if not self.messenger:
            if which_subapp == "Manager":
                self.messenger = ManagerMessenger(server, mport)
            else:
                self.messenger = Messenger(server, mport)
        try:
            self.messenger.start()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n" "{}".format(e)).exec_()
            self.messenger = None
            return

        try:
            self.messenger.requestAndSaveToken(user, pwd)
        except PlomAPIException as e:
            ErrorMessage(
                "Could not authenticate due to API mismatch."
                "Your client version is {}.\n\n"
                "Error was: {}".format(__version__, e)
            ).exec_()
            self.messenger = None
            return
        except PlomAuthenticationException as e:
            # not PlomAuthenticationException(blah) has args [PlomAuthenticationException, "you are not authenticated, blah] - we only want the blah.
            ErrorMessage("Could not authenticate: {}".format(e.args[-1])).exec_()
            self.messenger = None
            return
        except PlomExistingLoginException:
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
                self.messenger.clearAuthorisation(user, pwd)
            self.messenger = None
            return

        except PlomSeriousException as e:
            ErrorMessage(
                "Could not get authentication token.\n\n"
                "Unexpected error: {}".format(e)
            ).exec_()
            self.messenger = None
            return

        # TODO: implement shared tempdir/workfir for Marker/IDer & list in options dialog

        if which_subapp == "Manager":
            # Importing here avoids a circular import
            from plom.manager import Manager

            self.setEnabled(False)
            self.hide()
            window = Manager(
                self.parent,
                manager_msgr=self.messenger,
                server=server,
                user=user,
                password=pwd,
            )
            window.show()
            # store ref in Qapp to avoid garbase collection
            self.parent._manager_window = window
        elif which_subapp == "Marker":
            question = self.getQuestion()
            v = self.getv()
            self.setEnabled(False)
            self.hide()
            markerwin = MarkerClient(self.parent)
            markerwin.my_shutdown_signal.connect(self.on_marker_window_close)
            markerwin.show()
            markerwin.setup(self.messenger, question, v, self.lastTime)
            # store ref in Qapp to avoid garbase collection
            self.parent.marker = markerwin
        elif which_subapp == "Identifier":
            self.setEnabled(False)
            self.hide()
            idwin = IDClient()
            idwin.my_shutdown_signal.connect(self.on_other_window_close)
            idwin.show()
            idwin.setup(self.messenger)
            # store ref in Qapp to avoid garbase collection
            self.parent.identifier = idwin
        else:
            raise RuntimeError("Invalid subapplication value")

    def run_marker(self):
        self.validate("Marker")

    def run_identifier(self):
        self.validate("Identifier")

    def run_manager(self):
        self.validate("Manager")

    def saveDetails(self):
        self.lastTime["user"] = self.ui.userLE.text().strip()
        self.lastTime["server"] = "{}:{}".format(
            self.ui.serverLE.text().strip(), self.ui.mportSB.value()
        )
        self.lastTime["question"] = self.getQuestion()
        self.lastTime["v"] = self.getv()
        self.lastTime["fontSize"] = self.ui.fontSB.value()
        writeLastTime(self.lastTime)

    def closeWindow(self):
        self.saveDetails()
        if self.messenger:
            self.messenger.stop()
        self.close()

    def setFont(self, n):
        """Adjust font size of user interface.

        args:
            n (int): the desired font size in points.
        """
        fnt = self.parent.font()
        fnt.setPointSize(n)
        self.parent.setFont(fnt)

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
        except:
            return None

    def ungetInfo(self):
        self.ui.markGBox.setTitle("Marking information")
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
            self.messenger = Messenger(server, mport)
        try:
            ver = self.messenger.start()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n" "{}".format(e)).exec_()
            self.messenger = None
            return
        self.ui.infoLabel.setText(ver)

        try:
            spec = self.messenger.get_spec()
        except PlomSeriousException as e:
            ErrorMessage("Could not connect to server", info=str(e)).exec_()
            self.messenger = None
            return

        self.ui.markGBox.setTitle("Marking information for “{}”".format(spec["name"]))
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
            self.ui.passwordLE.setFocus(True)
        else:
            self.ui.userLE.setFocus(True)

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
        self.lastTime["SidebarOnRight"] = stuff[0]
