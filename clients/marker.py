# -*- coding: utf-8 -*-

"""
The Plom Marker client
"""

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import os
import json
import shutil
import sys
import tempfile
import time
import threading
import queue
import math

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QElapsedTimer,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    QTimer,
    QThread,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QWidget,
)


from examviewwindow import ExamViewWindow
import messenger
from annotator import Annotator
from useful_classes import AddTagBox, ErrorMessage, SimpleMessage
from reorientationwindow import ExamReorientWindow
from uiFiles.ui_marker import Ui_MarkerWindow
from client_utils import requestToken

# in order to get shortcuts under OSX this needs to set this.... but only osx.
# To test platform
import platform

if platform.system() == "Darwin":
    from PyQt5.QtGui import qt_set_sequence_auto_mnemonic

    qt_set_sequence_auto_mnemonic(True)

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import Plom_API_Version

# set up variables to store paths for marker and id clients
tempDirectory = tempfile.TemporaryDirectory(prefix="plom_")
directoryPath = tempDirectory.name

# Read https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
# and https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
# and finally https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
# I'll do it the simpler subclassing way
class BackgroundDownloader(QThread):
    downloadSuccess = pyqtSignal(str)
    downloadFail = pyqtSignal(str, str)
    # TODO: temporary stuff, eventually Messenger will know it
    _userName = None
    _token = None

    def __init__(self, tname, fname):
        QThread.__init__(self)
        self.tname = tname
        self.fname = fname

    def run(self):
        print(
            "Debug: downloader thread {}: downloading {}, {}".format(
                threading.get_ident(), self.tname, self.fname
            )
        )
        try:
            messenger.getFileDav_woInsanity(self.tname, self.fname)
        except Exception as ex:
            # TODO: just OperationFailed?  Just WebDavException?  Others pass thru?
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            errmsg = template.format(type(ex).__name__, ex.args)
            self.downloadFail.emit(self.tname, errmsg)
            self.quit()

        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg_nopopup(["mDWF", self._userName, self._token, self.tname])
        if msg[0] == "ACK":
            print(
                "Debug: downloader thread {}: got tname, fname={},{}".format(
                    threading.get_ident(), self.tname, self.fname
                )
            )
            self.downloadSuccess.emit(self.tname)
        else:
            errmsg = msg[1]
            print(
                "Debug: downloader thread {}: FAILED to get tname, fname={},{}".format(
                    threading.get_ident(), self.tname, self.fname
                )
            )
            self.downloadFail.emit(self.tname, errmsg)
        self.quit()


class BackgroundUploader(QThread):
    uploadSuccess = pyqtSignal(str, int, int)
    uploadFail = pyqtSignal(str, str)
    # TODO: temporary stuff, eventually Messenger will know it
    _userName = None
    _token = None

    def enqueueNewUpload(self, *args):
        """Place something in the upload queue

        Note: if you call this from the main thread, this code runs in the
        main thread.  That is ok b/c queue.Queue is threadsafe.  But its
        important to be aware, not all code in this object runs in the new
        thread: it depends where that code is called!
        """
        print("Debug: upQ enqueing new in thread " + str(threading.get_ident()))
        self.q.put(args)

    def empty(self):
        return self.q.empty()

    def run(self):
        def tryToUpload():
            # define this inside run so it will run in the new thread
            # https://stackoverflow.com/questions/52036021/qtimer-on-a-qthread
            from queue import Empty as EmptyQueueException

            try:
                code, gr, aname, pname, cname, mtime, pg, ver, tags = (
                    self.q.get_nowait()
                )
            except EmptyQueueException:
                return
            print(
                "Debug: upQ (thread {}): popped code {} from queue, uploading "
                "with webdav...".format(str(threading.get_ident()), code)
            )
            afile = os.path.basename(aname)
            pfile = os.path.basename(pname)
            cfile = os.path.basename(cname)
            try:
                messenger.putFileDav_woInsanity(aname, afile)
                messenger.putFileDav_woInsanity(pname, pfile)
                messenger.putFileDav_woInsanity(cname, cfile)
            except Exception as ex:
                # TODO: just OperationFailed?  Just WebDavException?  Others pass thru?
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                errmsg = template.format(type(ex).__name__, ex.args)
                self.uploadFail.emit(code, errmsg)
                return

            print(
                "Debug: upQ: sending marks for {} via mRMD cmd server...".format(code)
            )
            # ensure user is still authorised to upload this particular pageimage -
            # this may have changed depending on what else is going on.
            # TODO: remove, either rRMD will succeed or fail: don't precheck
            msg = messenger.SRMsg_nopopup(["mUSO", self._userName, self._token, code])
            if msg[0] != "ACK":
                errmsg = msg[1]
                print("Debug: upQ: emitting FAILED signal for {}".format(code))
                self.uploadFail.emit(code, errmsg)
            msg = messenger.SRMsg_nopopup(
                [
                    "mRMD",
                    self._userName,
                    self._token,
                    code,
                    gr,
                    afile,
                    pfile,
                    cfile,
                    mtime,
                    pg,
                    ver,
                    tags,
                ]
            )
            # self.sleep(4)  # pretend upload took longer
            if msg[0] == "ACK":
                numdone = msg[1]
                numtotal = msg[2]
                print("Debug: upQ: emitting SUCCESS signal for {}".format(code))
                self.uploadSuccess.emit(code, numdone, numtotal)
            else:
                errmsg = msg[1]
                print("Debug: upQ: emitting FAILED signal for {}".format(code))
                self.uploadFail.emit(code, errmsg)

        print("upQ.run: thread " + str(threading.get_ident()))
        self.q = queue.Queue()
        print("Debug: upQ: starting with new empty queue and starting timer")
        # TODO: Probably don't need the timer: after each enqueue, signal the
        # QThread (in the new thread's event loop) to call tryToUpload.
        timer = QTimer()
        timer.timeout.connect(tryToUpload)
        timer.start(250)
        self.exec_()


class TestPageGroup:
    """A simple container for storing a groupimage's code (tgv),
    numer, group, version, status, the mark, the original image
    filename, the annotated image filename, the mark, and the
    time spent marking the groupimage.
    """

    def __init__(self, tgv, fname="", stat="untouched", mrk="-1", mtime="0", tags=""):
        # tgv = t0000p00v0
        # ... = 0123456789
        # the test code
        self.prefix = tgv
        # the test number
        self.status = stat
        # By default set mark to be negative (since 0 is a possible mark)
        self.mark = mrk
        # The filename of the untouched image
        self.originalFile = fname
        # The filename for the (future) annotated image
        self.annotatedFile = ""
        # The filename for the (future) plom file
        self.plomFile = ""
        # The time spent marking the image.
        self.markingTime = mtime
        # Any user tags/comments
        self.tags = tags


class ExamModel(QStandardItemModel):
    """A tablemodel for handling the group image marking data."""

    def __init__(self, parent=None):
        QStandardItemModel.__init__(self, parent)
        self.setHorizontalHeaderLabels(
            [
                "TGV",
                "Status",
                "Mark",
                "Time",
                "Tag",
                "OriginalFile",
                "AnnotatedFile",
                "PlomFile",
                "PaperDir",
            ]
        )

    def addPaper(self, paper):
        # Append new groupimage to list and append new row to table.
        r = self.rowCount()
        self.appendRow(
            [
                QStandardItem(paper.prefix),
                QStandardItem(paper.status),
                QStandardItem(str(paper.mark)),
                QStandardItem(str(paper.markingTime)),
                QStandardItem(paper.tags),
                QStandardItem(paper.originalFile),
                QStandardItem(paper.annotatedFile),
                QStandardItem(paper.plomFile),
            ]
        )
        return r


##########################
class ProxyModel(QSortFilterProxyModel):
    """A proxymodel wrapper to put around the table model to handle filtering and sorting."""

    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.setFilterKeyColumn(4)
        self.filterString = ""

    def setFilterString(self, flt):
        self.filterString = flt

    def filterTags(self):
        self.setFilterFixedString(self.filterString)

    def filterAcceptsRow(self, pos, index):
        if len(self.filterString) == 0:
            return True
        if (
            self.filterString.casefold()
            in self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
        ):
            return True
        return False

    def addPaper(self, rho):
        # Append new groupimage to list and append new row to table.
        r = self.sourceModel().addPaper(rho)
        pr = self.mapFromSource(self.sourceModel().index(r, 0)).row()
        return pr

    def getPrefix(self, r):
        # Return the prefix of the image
        return self.data(self.index(r, 0))

    def getStatus(self, r):
        # Return the status of the image
        return self.data(self.index(r, 1))

    def setStatus(self, r, stat):
        # Return the status of the image
        return self.setData(self.index(r, 1), stat)

    def getOriginalFile(self, r):
        # Return the filename of the original un-annotated image
        return self.data(self.index(r, 5))

    def setOriginalFile(self, r, fname):
        # Set the original image filename
        self.setData(self.index(r, 5), fname)

    def setPaperDir(self, r, tdir):
        # Set the temporary directory for this grading
        self.setData(self.index(r, 8), tdir)

    def clearPaperDir(self, r):
        self.setPaperDir(r, None)

    def getPaperDir(self, r):
        return self.data(self.index(r, 8))

    def getAnnotatedFile(self, r):
        # Return the filename of the annotated image
        return self.data(self.index(r, 6))

    def setAnnotatedFile(self, r, aname, pname):
        # Set the annotated image filename
        self.setData(self.index(r, 6), aname)
        self.setData(self.index(r, 7), pname)

    def getPlomFile(self, r):
        # Return the filename of the plom file
        return self.data(self.index(r, 7))

    def markPaper(self, index, mrk, aname, pname, mtime, tdir):
        # When marked, set the annotated filename, the plomfile, the mark,
        # and the total marking time (in case it was annotated earlier)
        mt = int(self.data(index[3]))
        # total elapsed time.
        self.setData(index[3], mtime + mt)
        self.setData(index[1], "uploading...")
        self.setData(index[2], mrk)
        self.setData(index[0].siblingAtColumn(6), aname)
        self.setData(index[0].siblingAtColumn(7), pname)
        self.setData(index[0].siblingAtColumn(8), tdir)

    def revertPaper(self, index):
        # When user reverts to original image, set status to "reverted"
        # mark back to -1, and marking time to zero.
        # Do not erase any files: could still be uploading
        self.setData(index[1], "reverted")
        self.setData(index[2], -1)
        self.setData(index[3], 0)
        self.clearPaperDir(index[0].row())

    def deferPaper(self, index):
        # When user defers paper, it must be unmarked or reverted already. Set status to "deferred"
        self.setData(index[1], "deferred")


##########################


# TODO: should be a QMainWindow but at any rate not a Dialog
# TODO: should this be parented by the QApplication?
class MarkerClient(QWidget):
    my_shutdown_signal = pyqtSignal(int, list)

    def __init__(
        self,
        userName,
        password,
        server,
        message_port,
        web_port,
        pageGroup,
        version,
        lastTime,
    ):
        # Init the client with username, password, server and port data,
        # and which group/version is being marked.
        super(MarkerClient, self).__init__()
        # Fire up the messenger with server data.
        messenger.setServerDetails(server, message_port, web_port)
        messenger.startMessenger()
        # Ping to see if server is up.
        if not messenger.pingTest():
            QTimer.singleShot(100, self.shutDownError)
            self.testImg = None  # so that resize event doesn't throw error
            return
        # Save username, password, and path the local temp directory for
        # image files and the class list.
        self.userName = userName
        self.password = password
        self.workingDirectory = directoryPath
        # Save the group and version.
        self.pageGroup = pageGroup
        self.version = version
        # create max-mark, but not set until we get info from server
        self.maxScore = -1
        # For viewing the whole paper we'll need these two lists.
        self.viewFiles = []
        self.localViewFiles = []
        # Fire up the user interface
        self.ui = Ui_MarkerWindow()
        self.ui.setupUi(self)
        # Paste the username, pagegroup and version into GUI.
        self.ui.userLabel.setText(self.userName)
        self.ui.pgLabel.setText(str(self.pageGroup).zfill(2))
        self.ui.vLabel.setText(str(self.version))
        # Exam model for the table of groupimages - connect to table
        self.exM = ExamModel()
        # set proxy for filtering and sorting
        self.prxM = ProxyModel()
        self.prxM.setSourceModel(self.exM)
        self.ui.tableView.setModel(self.prxM)
        self.ui.tableView.hideColumn(5)  # hide original filename
        self.ui.tableView.hideColumn(6)  # hide annotated filename
        self.ui.tableView.hideColumn(7)  # hide plom filename
        self.ui.tableView.hideColumn(8)  # hide paperdir
        # Double-click or signale fires up the annotator window
        self.ui.tableView.doubleClicked.connect(self.annotateTest)
        self.ui.tableView.annotateSignal.connect(self.annotateTest)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.testImg = ExamViewWindow()
        self.ui.gridLayout_6.addWidget(self.testImg, 0, 0)
        # create a settings variable for saving annotator window settings
        # initially all settings are "none"
        self.annotatorSettings = defaultdict(lambda: None)
        # if lasttime["POWERUSER"] is true, the disable warnings in annotator
        if "POWERUSER" in lastTime:
            if lastTime["POWERUSER"]:
                self.annotatorSettings["markWarnings"] = False
                self.annotatorSettings["commentWarnings"] = False

        # Connect gui buttons to appropriate functions
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.revertButton.clicked.connect(self.revertTest)
        self.ui.deferButton.clicked.connect(self.deferTest)
        self.ui.tagButton.clicked.connect(self.tagTest)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        # self.ui.filterLE.focusInEvent.connect(lambda: self.ui.filterButton.setFocus())
        # Give IDs to the radio-buttons which select the marking style
        # 1 = mark total = user clicks the total-mark
        # 2 = mark-up = mark starts at 0 and user increments it
        # 3 = mark-down = mark starts at max and user decrements it
        # TODO: remove the total-radiobutton, but
        # for the timebeing we hide the totalrb from the user.
        self.ui.markStyleGroup.setId(self.ui.markTotalRB, 1)
        self.ui.markTotalRB.hide()
        self.ui.markTotalRB.setEnabled(False)
        # continue with the other buttons
        self.ui.markStyleGroup.setId(self.ui.markUpRB, 2)
        self.ui.markStyleGroup.setId(self.ui.markDownRB, 3)
        if lastTime["upDown"] == "up":
            self.ui.markUpRB.animateClick()
        elif lastTime["upDown"] == "down":
            self.ui.markDownRB.animateClick()

        # Give IDs to the radio buttons which select which mouse-hand is used
        # 0 = Right-handed user will typically have right-hand on mouse and
        # left hand on the keyboard. The annotator layout will follow this.
        # 1 = Left-handed user - reverse layout
        self.ui.mouseHandGroup.setId(self.ui.rightMouseRB, 0)
        self.ui.mouseHandGroup.setId(self.ui.leftMouseRB, 1)
        if lastTime["mouse"] == "right":
            self.ui.rightMouseRB.animateClick()
        elif lastTime["mouse"] == "left":
            self.ui.leftMouseRB.animateClick()

        # Start using connection to serverself.
        try:
            self.token = requestToken(self.userName, self.password)
        except ValueError as e:
            print("DEBUG: token fail: {}".format(e))
            QTimer.singleShot(100, self.shutDownError)
            return
        # Get the max-mark for the question from the server.
        try:
            self.getMaxMark()
        except ValueError as e:
            print("DEBUG: max-mark fail: {}".format(e))
            QTimer.singleShot(100, self.shutDownError)
            return
        # Paste the max-mark into the gui.
        self.ui.scoreLabel.setText(str(self.maxScore))
        # Get list of papers already marked and add to table.
        self.getMarkedList()
        # Update counts
        self.updateCount()
        # Connect the view **after** list updated.
        # Connect the table-model's selection change to appropriate function
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        # A simple cache table for latex'd comments
        self.commentCache = {}
        self.backgroundDownloader = None
        # Get a pagegroup to mark from the server
        self.requestNext()
        # reset the view so whole exam shown.
        self.testImg.resetB.animateClick()
        # resize the table too.
        QTimer.singleShot(100, self.ui.tableView.resizeRowsToContents)
        print("Debug: Marker main thread: " + str(threading.get_ident()))
        self.backgroundUploader = BackgroundUploader()
        self.backgroundUploader.uploadSuccess.connect(self.backgroundUploadFinished)
        self.backgroundUploader.uploadFail.connect(self.backgroundUploadFailed)
        self.backgroundUploader._userName = self.userName
        self.backgroundUploader._token = self.token
        self.backgroundUploader.start()
        # Now cache latex for comments:
        self.cacheLatexComments()

    def resizeEvent(self, e):
        if self.testImg is None:
            # pingtest must have failed, so do nothing.
            return
        # On resize used to resize the image to keep it all in view
        self.testImg.resetB.animateClick()
        # resize the table too.
        self.ui.tableView.resizeRowsToContents()
        super(MarkerClient, self).resizeEvent(e)

    def getMaxMark(self):
        """Return the max mark or raise ValueError."""
        # Send max-mark request (mGMX) to server
        msg = messenger.SRMsg(
            ["mGMX", self.userName, self.token, self.pageGroup, self.version]
        )
        # Return should be [ACK, maxmark]
        if not msg[0] == "ACK":
            raise ValueError(msg[1])
        self.maxScore = msg[1]

    def getMarkedList(self):
        # Ask server for list of previously marked papers
        msg = messenger.SRMsg(
            ["mGML", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        fname = os.path.join(self.workingDirectory, "markedList.txt")
        messenger.getFileDav(msg[1], fname)
        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, msg[1]])
        # Add those marked papers to our paper-list
        with open(fname) as json_file:
            markedList = json.load(json_file)
            for x in markedList:
                self.addTGVToList(
                    TestPageGroup(
                        x[0], fname="", stat="marked", mrk=x[2], mtime=x[3], tags=x[4]
                    ),
                    update=False,
                )

    def addTGVToList(self, paper, update=True):
        # Add a new entry (given inside paper) to the table and
        # select it and update the displayed page-group image
        # convert new row to proxyRow
        pr = self.prxM.addPaper(paper)
        if update is True:
            self.ui.tableView.selectRow(pr)
            self.updateImage(pr)

    def checkFiles(self, pr):
        tgv = self.prxM.getPrefix(pr)
        if self.prxM.getOriginalFile(pr) != "":
            return
        msg = messenger.SRMsg(["mGGI", self.userName, self.token, tgv])
        if msg[0] == "ERR":
            return
        paperdir = tempfile.mkdtemp(prefix=tgv + "_", dir=self.workingDirectory)
        print("Debug: create paperdir {} for already-graded download".format(paperdir))
        fname = os.path.join(self.workingDirectory, "{}.png".format(msg[1]))
        aname = os.path.join(paperdir, "G{}.png".format(msg[1][1:]))
        pname = os.path.join(paperdir, "G{}.plom".format(msg[1][1:]))
        self.prxM.setPaperDir(pr, paperdir)

        tfname = msg[2]  # the temp original image file on webdav
        taname = msg[3]  # the temp annotated image file on webdav
        tpname = msg[4]  # the temp plom file on webdav
        messenger.getFileDav(tfname, fname)
        # got original file so ask server to remove it.
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, tfname])
        self.prxM.setOriginalFile(pr, fname)
        # If there is an annotated image then get it.
        if taname is None:
            return
        messenger.getFileDav(taname, aname)
        messenger.getFileDav(tpname, pname)
        # got annotated image / plom file so ask server to remove it.
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, taname])
        self.prxM.setAnnotatedFile(pr, aname, pname)

    def updateImage(self, pr=0):
        # Here the system should check if imagefiles exist and grab if needed.
        self.checkFiles(pr)

        # Grab the group-image from file and display in the examviewwindow
        # If group has been marked then display the annotated file
        # Else display the original group image
        if self.prxM.getStatus(pr) in ("marked", "uploading...", "???"):
            self.testImg.updateImage(self.prxM.getAnnotatedFile(pr))
        else:
            self.testImg.updateImage(self.prxM.getOriginalFile(pr))
        # wait a moment and click the reset-view button
        QTimer.singleShot(100, self.testImg.view.resetView)
        # Give focus to the table (so enter-key fires up annotator)
        self.ui.tableView.setFocus()

    def updateCount(self):
        # ask server for marking-count update
        progress_msg = messenger.SRMsg(
            ["mPRC", self.userName, self.token, self.pageGroup, self.version]
        )
        # returns [ACK, #marked, #total]
        if progress_msg[0] == "ACK":
            self.ui.mProgressBar.setValue(progress_msg[1])
            self.ui.mProgressBar.setMaximum(progress_msg[2])

    def requestNext(self, launchAgain=False):
        """Ask the server for an unmarked paper (mNUM). Server should return
        message [ACK, test-code, temp-filename]. Get file from webdav, add to
        the list of papers and update the image.
        """
        # Ask server for next unmarked paper
        msg = messenger.SRMsg(
            ["mNUM", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        # Return message should be [ACK, code, temp-filename, tags]
        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, msg[1] + ".png")
        # Get file from the tempfilename in the webdav
        tname = msg[2]
        messenger.getFileDav(tname, fname)
        # Add the page-group to the list of things to mark
        self.addTGVToList(TestPageGroup(msg[1], fname, tags=msg[3]))
        # Ack that test received - server then deletes it from webdav
        msg = messenger.SRMsg(["mDWF", self.userName, self.token, tname])
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()
        # launch annotator on the new test
        # Note-launch-again is set to true when user just wants to get
        # the next test and get annotating directly.
        # When false the user stays at the marker window
        if msg[0] != "ERR" and launchAgain:
            # do not recurse, instead animate click
            # self.annotateTest()
            self.ui.annButton.animateClick()

    def requestNextInBackgroundStart(self):
        # Ask server for next unmarked paper
        msg = messenger.SRMsg(
            ["mNUM", self.userName, self.token, self.pageGroup, self.version]
        )
        if msg[0] == "ERR":
            return
        # Return message should be [ACK, code, temp-filename, tags]
        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, msg[1] + ".png")
        # Get file from the tempfilename in the webdav
        tname = msg[2]
        # Do this `messenger.getFileDav(tname, fname)` in another thread
        if self.backgroundDownloader:
            print("Previous Downloader: " + str(self.backgroundDownloader))
            # if prev downloader still going than wait.  might block the gui
            self.backgroundDownloader.wait()
        self.backgroundDownloader = BackgroundDownloader(tname, fname)
        self.backgroundDownloader._userName = self.userName
        self.backgroundDownloader._token = self.token
        self.backgroundDownloader.downloadSuccess.connect(
            self.requestNextInBackgroundFinished
        )
        self.backgroundDownloader.downloadFail.connect(
            self.requestNextInBackgroundFailed
        )
        self.backgroundDownloader.start()
        # Add the page-group to the list of things to mark
        # do not update the displayed image with this new paper
        self.addTGVToList(TestPageGroup(msg[1], fname, tags=msg[3]), update=False)

    def requestNextInBackgroundFinished(self, tname):
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundFailed(self, code, errmsg):
        # TODO what should we do?  Is there a realistic way forward
        # or should we just die with an exception?
        ErrorMessage(
            "Unfortunately, there was an unexpected error downloading "
            "paper {}.\n\n{}\n\n"
            "Please consider filing an issue?  I don't know if its "
            "safe to continue from here...".format(code, errmsg)
        ).exec_()

    def moveToNextUnmarkedTest(self):
        # Move to the next unmarked test in the table.
        # Be careful not to get stuck in a loop if all marked
        prt = self.prxM.rowCount()
        if prt == 0:
            return

        # back up one row because before this is called we have
        # added a row in the background, so the current row is actually
        # one too far forward.
        prstart = self.ui.tableView.selectedIndexes()[0].row()
        pr = prstart
        while self.prxM.getStatus(pr) in ["marked", "uploading...", "deferred", "???"]:
            pr = (pr + 1) % prt
            if pr == prstart:
                break
        self.ui.tableView.selectRow(pr)
        if pr == prstart:
            # gone right round, so select prstart+1
            self.ui.tableView.selectRow((pr + 1) % prt)
            return False
        return True

    def revertTest(self):
        """Get rid of any annotations or marks and go back to unmarked original"""
        # TODO: shouldn't the server be informed?
        # https://gitlab.math.ubc.ca/andrewr/MLP/issues/406
        # TODO: In particular, reverting the paper must not jump queue!
        prIndex = self.ui.tableView.selectedIndexes()
        # if no test then return
        if len(prIndex) == 0:
            return
        # If test is untouched or already reverted, nothing to do
        if self.prxM.data(prIndex[1]) in ["untouched", "reverted"]:
            return
        # Check user really wants to revert
        msg = SimpleMessage("Do you want to revert to original scan?")
        if msg.exec_() == QMessageBox.No:
            return
        # Revert the test in the table (set status, mark etc)
        self.prxM.revertPaper(prIndex)
        # Update the image (is now back to original untouched image)
        self.updateImage(prIndex[0].row())

    def deferTest(self):
        # Mark test as "defer" - to be skipped until later.
        index = self.ui.tableView.selectedIndexes()
        # if no test then return
        if len(index) == 0:
            return
        if self.prxM.data(index[1]) == "deferred":
            return
        if self.prxM.data(index[1]) in ("marked", "uploading...", "???"):
            msg = ErrorMessage("Paper is already marked - revert it before deferring.")
            msg.exec_()
            return
        self.prxM.deferPaper(index)

    def countUnmarkedReverted(self):
        count = 0
        for pr in range(self.prxM.rowCount()):
            if self.prxM.getStatus(pr) in ["untouched", "reverted"]:
                count += 1
        return count

    def waitForAnnotator(self, fname, pname=None):
        """This fires up the annotation window for user annotation + maring.
        Set a timer to record the time spend marking (for manager to see what
        questions are taking a long time or are quick).
        """
        # Set marking style total/up/down - will pass to annotator
        markStyle = self.ui.markStyleGroup.checkedId()
        # Set mousehand left/right - will pass to annotator
        mouseHand = self.ui.mouseHandGroup.checkedId()
        # Set plom-dictionary to none
        pdict = None
        # check if given a plom-file and override markstyle + pdict accordingly
        if pname is not None:
            with open(pname, "r") as fh:
                pdict = json.load(fh)
            markStyle = pdict["markStyle"]
            # TODO: there should be a filename sanity check here to
            # make sure plom file matches current image-file

        # Start a timer to record time spend annotating
        timer = QElapsedTimer()
        timer.start()
        # while annotator is firing up request next paper in background
        # after giving system a moment to do `annotator.exec_()`
        # but check if unmarked papers already in list.
        if self.countUnmarkedReverted() == 0:
            self.requestNextInBackgroundStart()
        # build the annotator - pass it the image filename, the max-mark
        # the markingstyle (up/down/total) and mouse-hand (left/right)
        annotator = Annotator(
            fname,
            self.maxScore,
            markStyle,
            mouseHand,
            parent=self,
            plomDict=pdict,
        )
        # run the annotator
        if annotator.exec_():
            # If annotator returns "accept"
            # then pass back the mark, time spent marking
            # (timer measures millisec, so divide by 1000)
            # and a flag as to whether or not we should relaunch the annotator
            # with the next page-image. In relaunch, then we will need to
            # ask server for next image.
            ret = [str(annotator.score), timer.elapsed() // 1000, annotator.launchAgain]
        else:
            # If annotator returns "reject", then pop up error
            msg = ErrorMessage("mark not recorded")
            msg.exec_()
            ret = [None, timer.elapsed(), False]
        return ret

    def annotateTest(self):
        """Command grabs current test from table and (after checks) passes it
        to 'waitForAnnotator' which fires up the actual annotator.
        Checks if current test has been marked already
        Saves the annotated file, mark, marking time etc in the table.
        Sends file and data back to server.
        """
        # If nothing in the table, return.
        if self.prxM.rowCount() == 0:
            return
        # Grab the currently selected row.
        index = self.ui.tableView.selectedIndexes()
        # mark sure something is selected
        if len(index) == 0:
            return
        # Create annotated filename. If original tXXXXgYYvZ.png, then
        # annotated version is GXXXXgYYvZ (G=graded).
        tgv = self.prxM.data(index[0])[1:]
        paperdir = tempfile.mkdtemp(prefix=tgv + "_", dir=self.workingDirectory)
        print("Debug: create paperdir {} for annotating".format(paperdir))
        aname = os.path.join(paperdir, "G" + tgv + ".png")
        cname = os.path.join(paperdir, "G" + tgv + ".json")
        pname = os.path.join(paperdir, "G" + tgv + ".plom")

        # If image has been marked confirm with user if they want
        # to annotate further.
        remarkFlag = False
        if self.prxM.data(index[1]) in ("marked", "uploading...", "???"):
            msg = SimpleMessage("Continue marking paper?")
            if not msg.exec_() == QMessageBox.Yes:
                return
            remarkFlag = True
            oldpaperdir = self.prxM.getPaperDir(index[0].row())
            print("Debug: oldpaperdir is " + oldpaperdir)
            assert oldpaperdir is not None
            oldaname = os.path.join(oldpaperdir, "G" + tgv + ".png")
            oldpname = os.path.join(oldpaperdir, "G" + tgv + ".plom")
            # oldcname = os.path.join(oldpaperdir, 'G' + tgv + ".json")
            # TODO: json file not downloaded
            # https://gitlab.math.ubc.ca/andrewr/MLP/issues/415
            shutil.copyfile(oldaname, aname)
            shutil.copyfile(oldpname, pname)
            # shutil.copyfile(oldcname, cname)

        # Yes do this even for a regrade!  We will recreate the annotations
        # (using the plom file) on top of the original file.
        fname = "{}".format(self.prxM.getOriginalFile(index[0].row()))
        if self.backgroundDownloader:
            count = 0
            # Notes: we could check using `while not os.path.exists(fname):`
            # Or we can wait on the downloader, which works when there is only
            # one download thread.  Better yet might be a dict/database that
            # we update on downloadFinished signal.
            while self.backgroundDownloader.isRunning():
                time.sleep(0.1)
                count += 1
                if math.remainder(count, 10) == 0:
                    print("Debug: waiting for downloader: {}".format(fname))
                if count >= 40:
                    msg = SimpleMessage(
                        "Still waiting for download.  Do you want to wait a bit longer?"
                    )
                    if msg.exec_() == QMessageBox.No:
                        return
                    count = 0

        # maybe the downloader failed for some (rare) reason
        if not os.path.exists(fname):
            return
        print("Debug: original image {} copy to paperdir {}".format(fname, paperdir))
        shutil.copyfile(fname, aname)

        # Get mark, markingtime, and launch-again flag from 'waitForAnnotator'
        prevState = self.prxM.data(index[1])
        self.prxM.setData(index[1], "annotating")
        if remarkFlag:
            [gr, mtime, launchAgain] = self.waitForAnnotator(aname, pname)
        else:
            [gr, mtime, launchAgain] = self.waitForAnnotator(aname, None)
        # Exited annotator with 'cancel', so don't save anything.
        if gr is None:
            # TODO: could also erase the paperdir
            # reselect the row we were working on
            self.prxM.setData(index[1], prevState)
            self.ui.tableView.selectRow(index[1].row())
            return
        # Copy the mark, annotated filename and the markingtime into the table
        self.prxM.markPaper(index, gr, aname, pname, mtime, paperdir)
        # Update the currently displayed image by selecting that row
        self.ui.tableView.selectRow(index[1].row())

        # the actual upload will happen in another thread
        self.backgroundUploader.enqueueNewUpload(
            "t" + tgv,  # current tgv
            gr,  # grade
            aname,  # annotated file
            pname,  # plom file
            cname,  # comment file
            mtime,  # marking time
            self.pageGroup,
            self.version,
            self.prxM.data(index[4]),  # tags
        )

        # Check if no unmarked test, then request one.
        if launchAgain is False:
            return
        if self.moveToNextUnmarkedTest():
            # self.annotateTest()
            self.ui.annButton.animateClick()

    def backgroundUploadFinished(self, code, numdone, numtotal):
        """An upload has finished, do appropriate UI updates"""
        for r in range(self.prxM.rowCount()):
            if self.prxM.getPrefix(r) == code:
                # maybe it changed while we waited for the upload
                if self.prxM.getStatus(r) == "uploading...":
                    self.prxM.setStatus(r, "marked")
        # TODO: negative used as invalid instead of None because the signal is typed
        if numdone > 0 and numtotal > 0:
            self.ui.mProgressBar.setValue(numdone)
            self.ui.mProgressBar.setMaximum(numtotal)

    def backgroundUploadFailed(self, code, errmsg):
        """An upload has failed, not sure what to do but do to it LOADLY"""
        for r in range(self.prxM.rowCount()):
            if self.prxM.getPrefix(r) == code:
                self.prxM.setStatus(r, "???")
        ErrorMessage(
            "Unfortunately, there was an unexpected error; server did "
            "not accept our marked paper {}.\n\n{}\n\n"
            "Please consider filing an issue?  Perhaps you could try "
            "annotating that paper again?".format(code, errmsg)
        ).exec_()

    def selChanged(self, selnew, selold):
        # When selection changed, update the displayed image
        idx = selnew.indexes()
        if len(idx) > 0:
            self.updateImage(idx[0].row())

    def shutDownError(self):
        self.my_shutdown_signal.emit(2, [])
        self.close()

    def shutDown(self):
        print("Debug: Marker shutdown from thread " + str(threading.get_ident()))
        if self.backgroundUploader:
            count = 42
            while self.backgroundUploader.isRunning():
                if self.backgroundUploader.empty():
                    # don't try to quit until the queue is empty
                    self.backgroundUploader.quit()
                time.sleep(0.1)
                count += 1
                if count >= 50:
                    count = 0
                    msg = SimpleMessage(
                        "Still waiting for uploader to finish.  Do you want to wait a bit longer?"
                    )
                    if msg.exec_() == QMessageBox.No:
                        # politely ask one more time
                        self.backgroundUploader.quit()
                        time.sleep(0.1)
                        # then nuke it from orbit
                        if self.backgroundUploader.isRunning():
                            self.backgroundUploader.terminate()
                        break
            self.backgroundUploader.wait()

        # When shutting down, first alert server of any images that were
        # not marked - using 'DNF' (did not finish). Sever will put
        # those files back on the todo pile.
        self.DNF()
        # Then send a 'user closing' message - server will revoke
        # authentication token.
        msg, = messenger.SRMsg(["UCL", self.userName, self.token])
        assert msg == "ACK"
        # set marking style, mousehand for return to client/parent
        markStyle = self.ui.markStyleGroup.checkedId()  # TODO
        mouseHand = self.ui.mouseHandGroup.checkedId()

        # finally send shutdown signal to client window and close.
        self.my_shutdown_signal.emit(2, [markStyle, mouseHand])
        self.close()

    def DNF(self):
        # Go through table and send a 'did not finish' message for anything
        # that is not marked.
        # Note - do this for everything, not just the proxy-model
        for r in range(self.exM.rowCount()):
            if self.exM.data(self.exM.index(r, 1)) != "marked":
                # Tell server the code fo any paper that is not marked.
                # server will put that back on the todo-pile.
                msg = messenger.SRMsg(
                    [
                        "mDNF",
                        self.userName,
                        self.token,
                        self.exM.data(self.exM.index(r, 0)),
                    ]
                )

    def viewWholePaper(self):
        index = self.ui.tableView.selectedIndexes()
        tgv = self.prxM.getPrefix(index[0].row())
        testnumber = tgv[1:5]  # since tgv = tXXXXgYYvZ
        msg = messenger.SRMsg(["mGWP", self.userName, self.token, testnumber])
        if msg[0] == "ERR":
            return []

        self.viewFiles = msg[1:]
        self.localViewFiles = []
        ## GIVE FILES NAMES
        for f in self.viewFiles:
            tfn = tempfile.NamedTemporaryFile(delete=False).name
            self.localViewFiles.append(tfn)
            messenger.getFileDav(f, tfn)
        return self.localViewFiles

    def doneWithViewFiles(self):
        for f in self.viewFiles:
            msg = messenger.SRMsg(["mDWF", self.userName, self.token, f])
        for f in self.localViewFiles:
            if os.path.isfile(f):
                os.unlink(f)
        self.localViewFiles = []
        self.viewFiles = []

    def cacheLatexComments(self):
        # grab the list of comments from disk
        if not os.path.exists("signedCommentList.json"):
            return
        clist = json.load(open("signedCommentList.json"))
        # sort list in order of longest comment to shortest comment
        clist.sort(key=lambda C: -len(C[1]))

        # Build a progress dialog to warn user
        pd = QProgressDialog("Caching latex comments", None, 0, 2 * len(clist), self)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)
        pd.setAutoClose(True)
        # Start caching.
        c = 0
        for X in clist:
            if X[1][:4].upper() == "TEX:":
                txt = X[1][4:].strip()
                pd.setLabelText("Caching:\n{}".format(txt[:64]))
                # latex the red version
                self.latexAFragment(txt)
                c += 1
                pd.setValue(c)
                # and latex the preview
                txtp = "\\color{blue}\n" + txt  # make color blue for ghost rendering
                self.latexAFragment(txtp)
                c += 1
                pd.setValue(c)
            else:
                c += 2
                pd.setValue(c)

    def latexAFragment(self, txt):
        if txt in self.commentCache:
            # have already latex'd this comment
            shutil.copyfile(self.commentCache[txt], "frag.png")
            return True

        # not yet present, so have to build it
        # create a tempfile
        fname = os.path.join(self.workingDirectory, "fragment")
        dname = (
            self.userName
        )  # call fragment file just the username to avoid collisions
        # write the latex text to that file
        with open(fname, "w") as fh:
            fh.write(txt)
        messenger.putFileDav(fname, dname)

        msg = messenger.SRMsg(["mLTT", self.userName, self.token, dname])
        if msg[1] == False:
            return False

        messenger.getFileDav(msg[2], "frag.png")
        messenger.SRMsg(["mDWF", self.userName, self.token, msg[2]])
        # now keep copy of frag.png for later use and update commentCache
        fragFile = tempfile.NamedTemporaryFile(
            delete=False, dir=self.workingDirectory
        ).name
        shutil.copyfile("frag.png", fragFile)
        self.commentCache[txt] = fragFile
        return True

    def tagTest(self):
        index = self.ui.tableView.selectedIndexes()
        tagSet = set()
        currentTag = self.prxM.data(index[4])

        for r in range(self.exM.rowCount()):
            v = self.exM.data(self.exM.index(r, 4))
            if len(v) > 0:
                tagSet.add(v)

        atb = AddTagBox(self, currentTag, list(tagSet))
        if atb.exec_() == QDialog.Accepted:
            txt = atb.TE.toPlainText().strip()
            # truncate at 256 characters.
            if len(txt) > 256:
                txt = txt[:256]

            self.prxM.setData(index[4], txt)
            # resize view too
            self.ui.tableView.resizeRowsToContents()

            # send updated tag back to server.
            msg = messenger.SRMsg(
                [
                    "mTAG",
                    self.userName,
                    self.token,
                    self.prxM.data(index[0]),
                    self.prxM.data(index[4]),  # send the tags back too
                ]
            )

        return

    def setFilter(self):
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        self.prxM.filterTags()
