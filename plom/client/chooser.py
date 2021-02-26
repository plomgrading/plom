# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
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
from plom.plom_exceptions import (
    PlomSeriousException,
    PlomBenignException,
    PlomAPIException,
    PlomAuthenticationException,
    PlomExistingLoginException,
)
from plom.messenger import Messenger
from plom.client.comment_list import comment_file

from .uiFiles.ui_chooser import Ui_Chooser
from .useful_classes import ErrorMessage, SimpleMessage, ClientSettingsDialog
from . import marker
from . import identifier


# TODO: for now, a global (to this module), later maybe in the QApp?
messenger = None

# set up variables to store paths for marker and id clients
global tempDirectory, directoryPath
# to store login + options for next run of client.
lastTime = {}

log = logging.getLogger("client")
logdir = Path(appdirs.user_log_dir("plom", "PlomGrading.org"))
cfgdir = Path(appdirs.user_config_dir("plom", "PlomGrading.org"))
cfgfile = cfgdir / "plomConfig.toml"


def readLastTime():
    """Read the login + server options that were used on
    the last run of the client.
    """
    global lastTime
    # set some reasonable defaults.
    lastTime["LogToFile"] = True  # default until stable release?
    lastTime["user"] = ""
    lastTime["server"] = "localhost"
    lastTime["question"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["upDown"] = "up"
    lastTime["mouse"] = "right"
    lastTime["CommentsWarnings"] = True
    lastTime["MarkWarnings"] = True
    # update default from config file
    if cfgfile.exists():
        # too early to log: log.info("Loading config file %s", cfgfile)
        with open(cfgfile) as f:
            lastTime.update(toml.load(f))


def writeLastTime():
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

        readLastTime()

        kwargs = {}
        if lastTime.get("LogToFile"):
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
        logging.getLogger().setLevel(lastTime.get("LogLevel", "Info").upper())

        s = "Plom Client {} (communicates with api {})".format(
            __version__, self.APIVersion
        )
        log.info(s)
        # runit = either marker or identifier clients.
        self.runIt = None

        self.ui = Ui_Chooser()
        self.ui.setupUi(self)
        # Append version to window title
        self.setWindowTitle("{} {}".format(self.windowTitle(), __version__))
        self.setLastTime()
        # connect buttons to functions.
        self.ui.markButton.clicked.connect(self.runMarker)
        self.ui.identifyButton.clicked.connect(self.runIDer)

        self.ui.closeButton.clicked.connect(self.closeWindow)
        self.ui.fontButton.clicked.connect(self.setFont)
        self.ui.optionsButton.clicked.connect(self.options)
        self.ui.getServerInfoButton.clicked.connect(self.getInfo)
        self.ui.serverLE.textEdited.connect(self.ungetInfo)
        self.ui.mportSB.valueChanged.connect(self.ungetInfo)
        self.ui.vDrop.setVisible(False)
        self.ui.pgDrop.setVisible(False)

    def setLastTime(self):
        # set login etc from last time client ran.
        self.ui.userLE.setText(lastTime["user"])
        self.setServer(lastTime["server"])
        self.ui.pgSB.setValue(int(lastTime["question"]))
        self.ui.vSB.setValue(int(lastTime["v"]))
        self.ui.fontSB.setValue(int(lastTime["fontSize"]))
        self.setFont()

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
            lastTime, logdir, cfgfile, tempfile.gettempdir(), comment_file
        )
        d.exec_()
        # TODO: do something more proper like QSettings
        stuff = d.getStuff()
        lastTime["FOREGROUND"] = stuff[0]
        lastTime["LogLevel"] = stuff[1]
        lastTime["LogToFile"] = stuff[2]
        lastTime["CommentsWarnings"] = stuff[3]
        lastTime["MarkWarnings"] = stuff[4]
        lastTime["mouse"] = "left" if stuff[5] else "right"
        lastTime["SidebarOnRight"] = stuff[6]
        logging.getLogger().setLevel(lastTime["LogLevel"].upper())

    def validate(self):
        # Check username is a reasonable string
        user = self.ui.userLE.text().strip()
        self.ui.userLE.setText(user)
        if (not user.isalnum()) or (not user):
            return
        # check password at least 4 char long
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

        try:
            # TODO: re-use existing messenger?
            messenger = Messenger(server, mport)
            messenger.start()
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
            # not PlomAuthenticationException(blah) has args [PlomAuthenticationException, "you are not authenticated, blah] - we only want the blah.
            ErrorMessage("Could not authenticate: {}".format(e.args[-1])).exec_()
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
            question = self.getQuestion()
            v = self.getv()
            self.setEnabled(False)
            self.hide()
            markerwin = marker.MarkerClient(self.parent)
            markerwin.my_shutdown_signal.connect(self.on_marker_window_close)
            markerwin.show()
            markerwin.setup(messenger, question, v, lastTime)
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
            # reserved for future use
            pass

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
        lastTime["user"] = self.ui.userLE.text().strip()
        lastTime["server"] = "{}:{}".format(
            self.ui.serverLE.text().strip(), self.ui.mportSB.value()
        )
        lastTime["question"] = self.getQuestion()
        lastTime["v"] = self.getv()
        lastTime["fontSize"] = self.ui.fontSB.value()
        writeLastTime()

    def closeWindow(self):
        self.saveDetails()
        if messenger:
            messenger.stop()
        self.close()

    def setFont(self):
        v = self.ui.fontSB.value()
        fnt = self.parent.font()
        fnt.setPointSize(v)
        self.parent.setFont(fnt)

    def getQuestion(self):
        """Return the integer question or None"""
        if self.ui.pgDrop.isVisible():
            question = self.ui.pgDrop.currentText().lstrip("Q")
        else:
            question = self.ui.pgSB.value()
        try:
            return int(question)
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
        # TODO: just `del messenger`?
        global messenger
        if messenger:
            messenger.stop()
        messenger = None

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

        try:
            messenger = Messenger(server, mport)
            r = messenger.start()
        except PlomBenignException as e:
            ErrorMessage("Could not connect to server.\n\n" "{}".format(e)).exec_()
            return
        self.ui.infoLabel.setText(r)

        try:
            spec = messenger.get_spec()
        except PlomSeriousException:
            try:
                spec = messenger.getInfoGeneral()
            except PlomSeriousException:
                ErrorMessage("Could not connect to server.").exec_()
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
            ["Q{}".format(x + 1) for x in range(0, spec["numberOfQuestions"])]
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
        # update mouse-hand and up/down style for lasttime file
        markStyle, mouseHand, sidebarRight = stuff
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
        lastTime["SidebarOnRight"] = sidebarRight
