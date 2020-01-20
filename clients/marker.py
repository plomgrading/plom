# -*- coding: utf-8 -*-

"""
The Plom Marker client
"""

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import os
import json
import shutil
import sys
import tempfile
import threading
import time
import toml
import queue

from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    QElapsedTimer,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    QTimer,
    QThread,
    pyqtSlot,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QWidget,
)


from examviewwindow import ExamViewWindow
import messenger
from annotator import Annotator
from plom_exceptions import *
from useful_classes import AddTagBox, ErrorMessage, SimpleMessage
from useful_classes import commentLoadAll, commentIsVisible
from reorientationwindow import ExamReorientWindow
from uiFiles.ui_marker import Ui_MarkerWindow
from test_view import GroupView, TestGroupSelect

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
    downloadSuccess = pyqtSignal(str, str, str)  # [tgv, file, tags]
    downloadNoneAvailable = pyqtSignal()
    downloadFail = pyqtSignal(str)

    def __init__(self, pg, v):
        QThread.__init__(self)
        self.pageGroup = pg
        self.version = v
        self.workingDirectory = directoryPath

    def run(self):
        attempts = 0
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            # ask server for tgv of next task
            try:
                test = messenger.MaskNextTask(self.pageGroup, self.version)
                if not test:  # no more tests left
                    self.downloadNoneAvailable.emit()
                    self.quit()
                    return
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

            try:
                image, tags = messenger.MclaimThisTask(test)
                break
            except PlomBenignException as err:
                # task taken by another user, so continue
                continue
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

        # Return message should be [ACK, True, code, temp-filename, tags]
        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, test + ".png")
        # save it
        with open(fname, "wb+") as fh:
            fh.write(image)
        self.downloadSuccess.emit(test, fname, tags)
        self.quit()


class BackgroundUploader(QThread):
    uploadSuccess = pyqtSignal(str, int, int)
    uploadFail = pyqtSignal(str, str)

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
                (
                    code,
                    gr,
                    aname,
                    pname,
                    cname,
                    mtime,
                    pg,
                    ver,
                    tags,
                ) = self.q.get_nowait()
            except EmptyQueueException:
                return
            print(
                "Debug: upQ (thread {}): popped code {} from queue, uploading".format(
                    str(threading.get_ident()), code
                )
            )
            # do name sanity check here
            if not (
                code.startswith("t")
                and os.path.basename(aname) == "G{}.png".format(code[1:])
                and os.path.basename(pname) == "G{}.plom".format(code[1:])
                and os.path.basename(cname) == "G{}.json".format(code[1:])
            ):
                raise PlomSeriousException(
                    "Upload file names mismatch [{}, {}, {}] - this should not happen".format(
                        fname, pname, cname
                    )
                )
            try:
                msg = messenger.MreturnMarkedTask(
                    code, pg, ver, gr, mtime, tags, aname, pname, cname
                )
            except Exception as ex:
                # TODO: just OperationFailed?  Just WebDavException?  Others pass thru?
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                errmsg = template.format(type(ex).__name__, ex.args)
                self.uploadFail.emit(code, errmsg)
                return

            numdone = msg[0]
            numtotal = msg[1]
            print("Debug: upQ: emitting SUCCESS signal for {}".format(code))
            self.uploadSuccess.emit(code, numdone, numtotal)

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

    def _getPrefix(self, r):
        # Return the prefix of the image
        return self.data(self.index(r, 0))

    def _getStatus(self, r):
        # Return the status of the image
        return self.data(self.index(r, 1))

    def _setStatus(self, r, stat):
        self.setData(self.index(r, 1), stat)

    def _getAnnotatedFile(self, r):
        # Return the filename of the annotated image
        return self.data(self.index(r, 6))

    def _setAnnotatedFile(self, r, aname, pname):
        # Set the annotated image filename
        self.setData(self.index(r, 6), aname)
        self.setData(self.index(r, 7), pname)

    def _setPaperDir(self, r, tdir):
        self.setData(self.index(r, 8), tdir)

    def _clearPaperDir(self, r):
        self._setPaperDir(r, None)

    def _getPaperDir(self, r):
        return self.data(self.index(r, 8))

    def _findTGV(self, tgv):
        """Return the row index of this tgv.

        Raises ValueError if not found.
        """
        r0 = []
        for r in range(self.rowCount()):
            if self._getPrefix(r) == tgv:
                r0.append(r)

        if len(r0) == 0:
            raise ValueError("tgv {} not found!".format(tgv))
        elif not len(r0) == 1:
            raise ValueError(
                "Repeated tgv {} in rows {}  This should not happen!".format(tgv, r0)
            )
        return r0[0]

    def _setDataByTGV(self, tgv, n, stuff):
        """Find the row with `tgv` and put `stuff` into `n`th column."""
        r = self._findTGV(tgv)
        self.setData(self.index(r, n), stuff)

    def _getDataByTGV(self, tgv, n):
        """Find the row with `tgv` and get the `n`th column."""
        r = self._findTGV(tgv)
        return self.data(self.index(r, n))

    def getStatusByTGV(self, tgv):
        """Return status for tgv"""
        return self._getDataByTGV(tgv, 1)

    def setStatusByTGV(self, tgv, st):
        """Set status for tgv"""
        self._setDataByTGV(tgv, 1, st)

    def getTagsByTGV(self, tgv):
        """Return tags for tgv"""
        return self._getDataByTGV(tgv, 4)

    def setTagsByTGV(self, tgv, tags):
        """Set tags for tgv"""
        return self._setDataByTGV(tgv, 4, tags)

    def getAllTags(self):
        """Return all tags as a set."""
        tags = set()
        for r in range(self.rowCount()):
            v = self.data(self.index(r, 4))
            if len(v) > 0:
                tags.add(v)
        return tags

    def getMTimeByTGV(self, tgv):
        """Return total marking time for tgv"""
        return int(self._getDataByTGV(tgv, 3))

    def getPaperDirByTGV(self, tgv):
        """Return temporary directory for this grading."""
        return self._getDataByTGV(tgv, 8)

    def setPaperDirByTGV(self, tgv, tdir):
        """Set temporary directory for this grading."""
        self._setDataByTGV(tgv, 8, tdir)

    def getOriginalFile(self, tgv):
        """Return filename for original un-annotated image."""
        return self._getDataByTGV(tgv, 5)

    def setOriginalFile(self, tgv, fname):
        """Set the original un-annotated image filename."""
        self._setDataByTGV(tgv, 5, fname)

    def setAnnotatedFile(self, tgv, aname, pname):
        """Set the annotated image and data filenames."""
        self._setDataByTGV(tgv, 6, aname)
        self._setDataByTGV(tgv, 7, pname)

    def markPaperByTGV(self, tgv, mrk, aname, pname, mtime, tdir):
        # There should be exactly one row with this TGV
        r = self._findTGV(tgv)
        # When marked, set the annotated filename, the plomfile, the mark,
        # and the total marking time (in case it was annotated earlier)
        mt = int(self.data(self.index(r, 3)))
        # total elapsed time.
        self.setData(self.index(r, 3), mtime + mt)
        self._setStatus(r, "uploading...")
        self.setData(self.index(r, 2), mrk)
        self._setAnnotatedFile(r, aname, pname)
        self._setPaperDir(r, tdir)

    def deferPaper(self, tgv):
        # When user defers paper, it must be unmarked or reverted already.
        # TODO: what is point of this comment?
        self.setStatusByTGV(tgv, "deferred")

    def revertPaper(self, tgv):
        # When user reverts to original image, set status to "reverted"
        # mark back to -1, and marking time to zero.
        r = self._findTGV(tgv)
        self._setStatus(r, "reverted")
        self.setData(self.index(r, 2), -1)
        self.setData(self.index(r, 3), 0)
        # Do not erase any files: could still be uploading
        self._clearPaperDir(r)

    def countReadyToMark(self):
        """Count how many are untouched or reverted."""
        count = 0
        for r in range(self.rowCount()):
            if self._getStatus(r) in ("untouched", "reverted"):
                count += 1
        return count


##########################
class ProxyModel(QSortFilterProxyModel):
    """A proxymodel wrapper to put around the table model to handle filtering and sorting."""

    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.setFilterKeyColumn(4)
        self.filterString = ""

    def lessThan(self, left, right):
        # Check to see if data is integer, and compare that
        try:
            lv = int(left.data())
            rv = int(right.data())
            return lv < rv
        except ValueError:
            # else let qt handle it.
            return left.data() < right.data()

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

    def getPrefix(self, r):
        # Return the prefix of the image
        return self.data(self.index(r, 0))

    def getStatus(self, r):
        # Return the status of the image
        return self.data(self.index(r, 1))

    def getOriginalFile(self, r):
        # Return the filename of the original un-annotated image
        return self.data(self.index(r, 5))

    def getAnnotatedFile(self, r):
        # Return the filename of the annotated image
        return self.data(self.index(r, 6))

    def rowFromTGV(self, tgv):
        """Return the row index of this tgv or None if absent."""
        r0 = []
        for r in range(self.rowCount()):
            if self.getPrefix(r) == tgv:
                r0.append(r)

        if len(r0) == 0:
            return None
        elif not len(r0) == 1:
            raise ValueError(
                "Repeated tgv {} in rows {}  This should not happen!".format(tgv, r0)
            )
        return r0[0]


##########################


# TODO: should be a QMainWindow but at any rate not a Dialog
# TODO: should this be parented by the QApplication?
class MarkerClient(QWidget):
    my_shutdown_signal = pyqtSignal(int, list)

    def __init__(self):
        super(MarkerClient, self).__init__()

    def getToWork(self, mess, testname, pageGroup, version, lastTime):
        # TODO or `self.msgr = mess`?  trouble in threads?
        global messenger
        messenger = mess
        # local temp directory for image files and the class list.
        self.workingDirectory = directoryPath
        # Save the group and version.
        self.testname = testname
        self.pageGroup = pageGroup
        self.version = version
        # create max-mark, but not set until we get info from server
        self.maxScore = -1
        # For viewing the whole paper we'll need these two lists.
        self.viewFiles = []
        # Fire up the user interface
        self.ui = Ui_MarkerWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('Plom Marker: "{}"'.format(self.testname))
        # Paste the username, pagegroup and version into GUI.
        self.ui.userBox.setTitle("User: {}".format(messenger.whoami()))
        self.ui.pgLabel.setText(
            "{} of {}".format(str(self.pageGroup).zfill(2), self.testname)
        )
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
                self.viewAll = True
        else:
            self.viewAll = False

        # Connect gui buttons to appropriate functions
        self.ui.closeButton.clicked.connect(self.shutDown)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.revertButton.clicked.connect(self.revertTest)
        self.ui.deferButton.clicked.connect(self.deferTest)
        self.ui.tagButton.clicked.connect(self.tagTest)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        self.ui.viewButton.clicked.connect(self.viewSpecificImage)
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

        # Start using connection to server.
        # Get the number of Tests, Pages, Questions and Versions
        try:
            self.testInfo = messenger.getInfoGeneral()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Get the max-mark for the question from the server.
        try:
            self.getMaxMark()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return
        # Paste the max-mark into the gui.
        self.ui.scoreLabel.setText(str(self.maxScore))

        # Get list of papers already marked and add to table.
        try:
            self.getMarkedList()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Update counts
        self.updateProgress()
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
        self.backgroundUploader.start()
        # Now cache latex for comments:
        self.cacheLatexComments()

    def resizeEvent(self, e):
        # a resize can be triggered before we "getToWork" is called.
        if hasattr(self, "testImg"):
            # On resize used to resize the image to keep it all in view
            self.testImg.resetB.animateClick()
        # resize the table too.
        if hasattr(self, "ui.tableView"):
            self.ui.tableView.resizeRowsToContents()
        super(MarkerClient, self).resizeEvent(e)

    def throwSeriousError(self, err):
        ErrorMessage(
            'A serious error has been thrown:\n"{}".\nCannot recover from this, so shutting down totaller.'.format(
                err
            )
        ).exec_()
        self.shutDownError()

    def throwBenign(self, err):
        ErrorMessage('A benign exception has been thrown:\n"{}".'.format(err)).exec_()

    def getMaxMark(self):
        """Get max mark from server and set."""
        # Send max-mark request (mGMX) to server
        self.maxScore = messenger.MgetMaxMark(self.pageGroup, self.version)

    def getMarkedList(self):
        # Ask server for list of previously marked papers
        markedList = messenger.MrequestDoneTasks(self.pageGroup, self.version)
        for x in markedList:
            # TODO: might not the "markedList" have some other statuses?
            self.exM.addPaper(
                TestPageGroup(
                    x[0], fname="", stat="marked", mrk=x[2], mtime=x[3], tags=x[4]
                )
            )

    def checkAndGrabFiles(self, tgv):
        # TODO: doesn't seem to do a lot of checking, despite name
        if self.exM.getOriginalFile(tgv) != "":
            return

        try:
            [image, anImage, plImage] = messenger.MrequestImages(tgv)
        except PlomSeriousException as e:
            self.throwSeriousError(e)
            return

        paperdir = tempfile.mkdtemp(prefix=tgv + "_", dir=self.workingDirectory)
        print("Debug: create paperdir {} for already-graded download".format(paperdir))
        fname = os.path.join(self.workingDirectory, "{}.png".format(tgv))
        with open(fname, "wb+") as fh:
            fh.write(image)
        self.exM.setOriginalFile(tgv, fname)

        if anImage is None:
            return

        self.exM.setPaperDirByTGV(tgv, paperdir)
        aname = os.path.join(paperdir, "G{}.png".format(tgv[1:]))
        pname = os.path.join(paperdir, "G{}.plom".format(tgv[1:]))
        with open(aname, "wb+") as fh:
            fh.write(anImage)
        with open(pname, "wb+") as fh:
            fh.write(plImage)
        self.exM.setAnnotatedFile(tgv, aname, pname)

    def updateImage(self, pr=0):
        # Here the system should check if imagefiles exist and grab if needed.
        self.checkAndGrabFiles(self.prxM.getPrefix(pr))

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

    def updateProgress(self):
        # ask server for progress update
        try:
            v, m = messenger.MprogressCount(self.pageGroup, self.version)
            self.ui.mProgressBar.setMaximum(m)
            self.ui.mProgressBar.setValue(v)
        except PlomSeriousException as err:
            self.throwSeriousError(err)

    def requestNext(self):
        """Ask the server for an unmarked paper.  Get file, add to
        the list of papers and update the image.
        """
        attempts = 0
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            # ask server for tgv of next task
            try:
                test = messenger.MaskNextTask(self.pageGroup, self.version)
                if not test:
                    return False
            except PlomSeriousException as err:
                self.throwSeriousError(err)

            try:
                [image, tags] = messenger.MclaimThisTask(test)
                break
            except PlomBenignException as err:
                # task already taken.
                continue

        # Code is tXXXXgYYvZ - so save as tXXXXgYYvZ.png
        fname = os.path.join(self.workingDirectory, test + ".png")
        # save it
        with open(fname, "wb+") as fh:
            fh.write(image)
        self.exM.addPaper(TestPageGroup(test, fname, tags=tags))
        pr = self.prxM.rowFromTGV(test)
        if pr is not None:
            # if newly-added row is visible, select it and redraw
            self.ui.tableView.selectRow(pr)
            self.updateImage(pr)
            # Clean up the table
            self.ui.tableView.resizeColumnsToContents()
            self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundStart(self):
        if self.backgroundDownloader:
            print("Previous Downloader: " + str(self.backgroundDownloader))
            # if prev downloader still going than wait.  might block the gui
            self.backgroundDownloader.wait()
        self.backgroundDownloader = BackgroundDownloader(self.pageGroup, self.version)
        self.backgroundDownloader.downloadSuccess.connect(
            self.requestNextInBackgroundFinished
        )
        self.backgroundDownloader.downloadNoneAvailable.connect(
            self.requestNextInBackgroundNoneAvailable
        )
        self.backgroundDownloader.downloadFail.connect(
            self.requestNextInBackgroundFailed
        )
        self.backgroundDownloader.start()

    def requestNextInBackgroundFinished(self, test, fname, tags):
        self.exM.addPaper(TestPageGroup(test, fname, tags=tags))
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundNoneAvailable(self):
        # Keep this function here just in case we want to do something in the future.
        pass

    def requestNextInBackgroundFailed(self, errmsg):
        # TODO what should we do?  Is there a realistic way forward
        # or should we just die with an exception?
        ErrorMessage(
            "Unfortunately, there was an unexpected error downloading "
            "next paper.\n\n{}\n\n"
            "Please consider filing an issue?  I don't know if its "
            "safe to continue from here...".format(errmsg)
        ).exec_()

    def moveToNextUnmarkedTest(self, tgv):
        # Move to the next unmarked test in the table.
        # Be careful not to get stuck in a loop if all marked
        prt = self.prxM.rowCount()
        if prt == 0:
            return  # TODO True or False?
        # get current position from the tgv
        prstart = self.prxM.rowFromTGV(tgv)
        if not prstart:
            # it might be hidden by filters
            prstart = 0
        pr = prstart
        while self.prxM.getStatus(pr) in ["marked", "uploading...", "deferred", "???"]:
            pr = (pr + 1) % prt
            if pr == prstart:
                break
        if pr == prstart:
            return False
        self.ui.tableView.selectRow(pr)
        return True

    def revertTest(self):
        """Get rid of any annotations or marks and go back to unmarked original"""
        # TODO: shouldn't the server be informed?
        # https://gitlab.math.ubc.ca/andrewr/MLP/issues/406
        # TODO: In particular, reverting the paper must not jump queue!
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        tgv = self.prxM.getPrefix(pr)
        # If test is untouched or already reverted, nothing to do
        if self.exM.getStatusByTGV(tgv) in ("untouched", "reverted"):
            return
        # Check user really wants to revert
        msg = SimpleMessage("Do you want to revert to original scan?")
        if msg.exec_() == QMessageBox.No:
            return
        # Revert the test in the table (set status, mark etc)
        self.exM.revertPaper(tgv)
        # Update the image (is now back to original untouched image)
        self.updateImage(pr)

    def deferTest(self):
        """Mark test as "defer" - to be skipped until later."""
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        tgv = self.prxM.getPrefix(pr)
        if self.exM.getStatusByTGV(tgv) == "deferred":
            return
        if self.exM.getStatusByTGV(tgv) in ("marked", "uploading...", "???"):
            msg = ErrorMessage("Paper is already marked - revert it before deferring.")
            msg.exec_()
            return
        self.exM.deferPaper(tgv)

    def startTheAnnotator(self, tgv, paperdir, fname, pname=None):
        """This fires up the annotation window for user annotation + marking."""
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

        # while annotator is firing up request next paper in background
        # after giving system a moment to do `annotator.exec_()`
        if self.exM.countReadyToMark() == 0:
            self.requestNextInBackgroundStart()
        # build the annotator - pass it the image filename, the max-mark
        # the markingstyle (up/down/total) and mouse-hand (left/right)
        annotator = Annotator(
            tgv,
            self.testname,
            paperdir,
            fname,
            self.maxScore,
            markStyle,
            mouseHand,
            parent=self,
            plomDict=pdict,
        )
        # run the annotator
        annotator.ann_finished_accept.connect(self.callbackAnnIsDoneAccept)
        annotator.ann_finished_reject.connect(self.callbackAnnIsDoneCancel)
        self.setEnabled(False)
        annotator.show()

    def annotateTest(self):
        """Grab current test from table, do checks, start annotator."""
        if len(self.ui.tableView.selectedIndexes()):
            row = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        tgv = self.prxM.getPrefix(row)
        # split fcn: maybe we want to start the annotator not based on current selection
        self.annotateTest_doit(tgv)

    def annotateTest_doit(self, tgv):
        """Start annotator on a particular tgv."""
        # Create annotated filename. If original tXXXXgYYvZ.png, then
        # annotated version is GXXXXgYYvZ (G=graded).
        assert tgv.startswith("t")
        Gtgv = "G" + tgv[1:]
        paperdir = tempfile.mkdtemp(prefix=tgv[1:] + "_", dir=self.workingDirectory)
        print("Debug: create paperdir {} for annotating".format(paperdir))
        aname = os.path.join(paperdir, Gtgv + ".png")
        cname = os.path.join(paperdir, Gtgv + ".json")
        pname = os.path.join(paperdir, Gtgv + ".plom")

        # If image has been marked confirm with user if they want
        # to annotate further.
        remarkFlag = False

        if self.exM.getStatusByTGV(tgv) in ("marked", "uploading...", "???"):
            msg = SimpleMessage("Continue marking paper?")
            if not msg.exec_() == QMessageBox.Yes:
                return
            remarkFlag = True
            oldpaperdir = self.exM.getPaperDirByTGV(tgv)
            print("Debug: oldpaperdir is " + oldpaperdir)
            assert oldpaperdir is not None
            oldaname = os.path.join(oldpaperdir, Gtgv + ".png")
            oldpname = os.path.join(oldpaperdir, Gtgv + ".plom")
            # oldcname = os.path.join(oldpaperdir, Gtgv + ".json")
            # TODO: json file not downloaded
            # https://gitlab.math.ubc.ca/andrewr/MLP/issues/415
            shutil.copyfile(oldaname, aname)
            shutil.copyfile(oldpname, pname)
            # shutil.copyfile(oldcname, cname)

        # Yes do this even for a regrade!  We will recreate the annotations
        # (using the plom file) on top of the original file.
        fname = "{}".format(self.exM.getOriginalFile(tgv))
        if self.backgroundDownloader:
            count = 0
            # Notes: we could check using `while not os.path.exists(fname):`
            # Or we can wait on the downloader, which works when there is only
            # one download thread.  Better yet might be a dict/database that
            # we update on downloadFinished signal.
            while self.backgroundDownloader.isRunning():
                time.sleep(0.1)
                count += 1
                # if .remainder(count, 10) == 0: # this is only python3.7 and later. - see #509
                if (count % 10) == 0:
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

        # stash the previous state, not ideal because makes column wider
        prevState = self.exM.getStatusByTGV(tgv)
        self.exM.setStatusByTGV(tgv, "ann:" + prevState)

        if remarkFlag:
            self.startTheAnnotator(tgv[1:], paperdir, aname, pname)
        else:
            self.startTheAnnotator(tgv[1:], paperdir, aname, None)
        # we started the annotator, we'll get a signal back when its done

    # when the annotator is done, we end up here...
    @pyqtSlot(str, list)
    def callbackAnnIsDoneCancel(self, tgv, stuff):
        self.setEnabled(True)
        assert not stuff  # currently nothing given back on cancel
        prevState = self.exM.getStatusByTGV("t" + tgv).split(":")[-1]
        # TODO: could also erase the paperdir
        self.exM.setStatusByTGV("t" + tgv, prevState)

    # ... or here
    @pyqtSlot(str, list)
    def callbackAnnIsDoneAccept(self, tgv, stuff):
        self.setEnabled(True)
        gr, launchAgain, mtime, paperdir, aname, pname, cname = stuff

        if not (0 <= gr and gr <= self.maxScore):
            msg = ErrorMessage(
                "Mark of {} is outside allowed range. Rejecting. This should not happen. Please file a bug".format(
                    self.annotator.score
                )
            )
            msg.exec_()
            # TODO: what do do here?  revert?
            return

        # Copy the mark, annotated filename and the markingtime into the table
        # TODO: sort this out whether tgv is "t00..." or "00..."?!
        self.exM.markPaperByTGV("t" + tgv, gr, aname, pname, mtime, paperdir)
        # update the mtime to be the total marking time
        totmtime = self.exM.getMTimeByTGV("t" + tgv)
        tags = self.exM.getTagsByTGV("t" + tgv)

        # the actual upload will happen in another thread
        self.backgroundUploader.enqueueNewUpload(
            "t" + tgv,  # current tgv
            gr,  # grade
            aname,  # annotated file
            pname,  # plom file
            cname,  # comment file
            totmtime,  # total marking time
            self.pageGroup,
            self.version,
            tags,
        )

        if launchAgain is False:
            # update image view, if the row we just finished is selected
            prIndex = self.ui.tableView.selectedIndexes()
            if len(prIndex) == 0:
                return
            pr = prIndex[0].row()
            if self.prxM.getPrefix(pr) == "t" + tgv:
                self.updateImage(pr)
            return
        if self.moveToNextUnmarkedTest("t" + tgv):
            # self.annotateTest()
            self.ui.annButton.animateClick()

    def backgroundUploadFinished(self, code, numdone, numtotal):
        """An upload has finished, do appropriate UI updates"""
        stat = self.exM.getStatusByTGV(code)
        # maybe it changed while we waited for the upload
        if stat == "uploading...":
            self.exM.setStatusByTGV(code, "marked")
        if numdone > 0 and numtotal > 0:
            self.ui.mProgressBar.setValue(numdone)
            self.ui.mProgressBar.setMaximum(numtotal)

    def backgroundUploadFailed(self, code, errmsg):
        """An upload has failed, not sure what to do but do to it LOADLY"""
        self.exM.setStatusByTGV(code, "???")
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
        try:
            messenger.closeUser()
        except PlomSeriousException as err:
            self.throwSeriousError(err)

        markStyle = self.ui.markStyleGroup.checkedId()
        mouseHand = self.ui.mouseHandGroup.checkedId()
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
                try:
                    messenger.MdidNotFinishTask(self.exM.data(self.exM.index(r, 0)))
                except PlomSeriousException as err:
                    self.throwSeriousError(err)

    def viewWholePaper(self):
        index = self.ui.tableView.selectedIndexes()
        tgv = self.prxM.getPrefix(index[0].row())
        testnumber = tgv[1:5]  # since tgv = tXXXXgYYvZ
        try:
            imagesAsBytes = messenger.MrequestWholePaper(testnumber)
        except PlomBenignException as err:
            self.throwBenign(err)

        self.viewFiles = []
        for iab in imagesAsBytes:
            tfn = tempfile.NamedTemporaryFile(delete=False).name
            self.viewFiles.append(tfn)
            with open(tfn, "wb") as fh:
                fh.write(iab)

        return self.viewFiles

    def doneWithViewFiles(self):
        for f in self.viewFiles:
            if os.path.isfile(f):
                os.unlink(f)
        self.viewFiles = []

    def cacheLatexComments(self):
        clist = commentLoadAll()
        # sort list in order of longest comment to shortest comment
        clist.sort(key=lambda C: -len(C["text"]))

        # Build a progress dialog to warn user
        pd = QProgressDialog("Caching latex comments", None, 0, 2 * len(clist), self)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)
        pd.setAutoClose(True)
        # Start caching.
        c = 0
        n = int(self.pageGroup)
        testname = self.testname
        for X in clist:
            if commentIsVisible(X, n, testname) and X["text"][:4].upper() == "TEX:":
                txt = X["text"][4:].strip()
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

        try:
            fragment = messenger.MlatexFragment(txt)
        except PlomLatexException as err:
            # a latex error
            return False
        # a name for the fragment file
        fragFile = tempfile.NamedTemporaryFile(
            delete=False, dir=self.workingDirectory
        ).name
        # save it
        with open(fragFile, "wb+") as fh:
            fh.write(fragment)
        # and put a copy to frag.png
        shutil.copyfile(fragFile, "frag.png")
        # add it to the cache
        self.commentCache[txt] = fragFile
        return True

    def tagTest(self):
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        tgv = self.prxM.getPrefix(pr)
        tagSet = self.exM.getAllTags()
        currentTag = self.exM.getTagsByTGV(tgv)

        atb = AddTagBox(self, currentTag, list(tagSet))
        if atb.exec_() == QDialog.Accepted:
            txt = atb.TE.toPlainText().strip()
            # truncate at 256 characters.  TODO: without warning?
            if len(txt) > 256:
                txt = txt[:256]

            self.exM.setTagsByTGV(tgv, txt)
            # resize view too
            self.ui.tableView.resizeRowsToContents()

            # send updated tag back to server.
            try:
                msg = messenger.MsetTag(tgv, txt)
            except PlomSeriousException as err:
                self.throwSeriousError(err)
        return

    def setFilter(self):
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        self.prxM.filterTags()

    def viewSpecificImage(self):
        if self.viewAll:
            tgs = TestGroupSelect(self.testInfo, self.pageGroup)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = tgs.gsb.value()
            else:
                return
        else:
            tgs = TestGroupSelect(self.testInfo)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = self.pageGroup
            else:
                return
        try:
            image = messenger.MrequestOriginalImage(tn, gn)
        except PlomNoMoreException as err:
            msg = ErrorMessage(
                "No image corresponding to test {} pageGroup {}".format(
                    tn, self.pageGroup
                )
            )
            msg.exec_()
            return
        ifile = tempfile.NamedTemporaryFile(dir=self.workingDirectory)
        with open(ifile.name, "wb") as fh:
            fh.write(image)
        tvw = GroupView(ifile.name)
        tvw.setWindowTitle(
            "Original ungraded image for question {} of test {}".format(gn, tn)
        )
        tvw.exec_()
