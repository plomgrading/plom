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
import logging

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

from .examviewwindow import ExamViewWindow
from .annotator import Annotator
from plom.plom_exceptions import *
from .useful_classes import ErrorMessage, SimpleMessage
from .comment_list import AddTagBox, commentLoadAll, commentIsVisible
from .reorientationwindow import ExamReorientWindow
from .uiFiles.ui_marker import Ui_MarkerWindow
from .origscansviewer import GroupView, SelectTestQuestion
from plom import Plom_API_Version

# in order to get shortcuts under OSX this needs to set this.... but only osx.
# To test platform
import platform

if platform.system() == "Darwin":
    from PyQt5.QtGui import qt_set_sequence_auto_mnemonic

    qt_set_sequence_auto_mnemonic(True)

log = logging.getLogger("marker")

# set up variables to store paths for marker and id clients
tempDirectory = tempfile.TemporaryDirectory(prefix="plom_")
directoryPath = tempDirectory.name

# Read https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
# and https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
# and finally https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
# I'll do it the simpler subclassing way
class BackgroundDownloader(QThread):
    downloadSuccess = pyqtSignal(str, list, str)  # [task, files, tags]
    downloadNoneAvailable = pyqtSignal()
    downloadFail = pyqtSignal(str)

    def __init__(self, qu, v):
        QThread.__init__(self)
        self.question = qu
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
            # ask server for task-code of next task
            try:
                task = messenger.MaskNextTask(self.question, self.version)
                if not task:  # no more tests left
                    self.downloadNoneAvailable.emit()
                    self.quit()
                    return
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()
                return

            try:
                imageList, tags = messenger.MclaimThisTask(task)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

        # Image names = "<task>.<imagenumber>.png"
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(self.workingDirectory, "{}.{}.png".format(task, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])
        self.downloadSuccess.emit(task, inames, tags)
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
        log.debug("upQ enqueing item from main thread " + str(threading.get_ident()))
        self.q.put(args)

    def isEmpty(self):
        return self.q.empty()

    def run(self):
        def tryToUpload():
            # define this inside run so it will run in the new thread
            # https://stackoverflow.com/questions/52036021/qtimer-on-a-qthread
            from queue import Empty as EmptyQueueException

            try:
                data = self.q.get_nowait()
            except EmptyQueueException:
                return
            code = data[0]  # TODO: remove so that queue needs no knowledge of args
            log.info("upQ thread: popped code {} from queue, uploading".format(code))
            upload(
                *data,
                failcallback=self.uploadFail.emit,
                successcallback=self.uploadSuccess.emit
            )

        self.q = queue.Queue()
        log.info("upQ thread: starting with new empty queue and starting timer")
        # TODO: Probably don't need the timer: after each enqueue, signal the
        # QThread (in the new thread's event loop) to call tryToUpload.
        timer = QTimer()
        timer.timeout.connect(tryToUpload)
        timer.start(250)
        self.exec_()


def upload(
    code, gr, filenames, mtime, qu, ver, tags, failcallback=None, successcallback=None,
):
    # do name sanity checks here
    aname, pname, cname = filenames
    if not (
        code.startswith("m")
        and os.path.basename(aname) == "G{}.png".format(code[1:])
        and os.path.basename(pname) == "G{}.plom".format(code[1:])
        and os.path.basename(cname) == "G{}.json".format(code[1:])
    ):
        raise PlomSeriousException(
            "Upload file names mismatch [{}, {}, {}] - this should not happen".format(
                aname, pname, cname
            )
        )
    try:
        msg = messenger.MreturnMarkedTask(
            code, qu, ver, gr, mtime, tags, aname, pname, cname
        )
    except Exception as ex:
        # TODO: just OperationFailed?  Just WebDavException?  Others pass thru?
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        errmsg = template.format(type(ex).__name__, ex.args)
        failcallback(code, errmsg)
        return

    numdone = msg[0]
    numtotal = msg[1]
    successcallback(code, numdone, numtotal)


class Testquestion:
    """A simple container for storing a groupimage's code (task),
    numer, group, version, status, the mark, the original image
    filename, the annotated image filename, the mark, and the
    time spent marking the groupimage.
    """

    def __init__(self, task, fnames=[], stat="untouched", mrk="-1", mtime="0", tags=""):
        # task will be of the form m1234g9 = test 1234 question 9
        # ... = 0123456789
        # the test code
        self.prefix = task
        # the test number
        self.status = stat
        # By default set mark to be negative (since 0 is a possible mark)
        self.mark = mrk
        # The filename of the untouched image
        self.originalFiles = fnames
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
                "Task",
                "Status",
                "Mark",
                "Time",
                "Tag",
                "OriginalFiles",
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
                # TODO - work out how to store list more directly rather than as a string-rep of the list of file names.
                QStandardItem(repr(paper.originalFiles)),
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

    def _findTask(self, task):
        """Return the row index of this task.

        Raises ValueError if not found.
        """
        r0 = []
        for r in range(self.rowCount()):
            if self._getPrefix(r) == task:
                r0.append(r)

        if len(r0) == 0:
            raise ValueError("task {} not found!".format(task))
        elif not len(r0) == 1:
            raise ValueError(
                "Repeated task {} in rows {}  This should not happen!".format(task, r0)
            )
        return r0[0]

    def _setDataByTask(self, task, n, stuff):
        """Find the row with `task` and put `stuff` into `n`th column."""
        r = self._findTask(task)
        self.setData(self.index(r, n), stuff)

    def _getDataByTask(self, task, n):
        """Find the row with `task` and get the `n`th column."""
        r = self._findTask(task)
        return self.data(self.index(r, n))

    def getStatusByTask(self, task):
        """Return status for task"""
        return self._getDataByTask(task, 1)

    def setStatusByTask(self, task, st):
        """Set status for task"""
        self._setDataByTask(task, 1, st)

    def getTagsByTask(self, task):
        """Return tags for task"""
        return self._getDataByTask(task, 4)

    def setTagsByTask(self, task, tags):
        """Set tags for task"""
        return self._setDataByTask(task, 4, tags)

    def getAllTags(self):
        """Return all tags as a set."""
        tags = set()
        for r in range(self.rowCount()):
            v = self.data(self.index(r, 4))
            if len(v) > 0:
                tags.add(v)
        return tags

    def getMTimeByTask(self, task):
        """Return total marking time for task"""
        return int(self._getDataByTask(task, 3))

    def getPaperDirByTask(self, task):
        """Return temporary directory for this grading."""
        return self._getDataByTask(task, 8)

    def setPaperDirByTask(self, task, tdir):
        """Set temporary directory for this grading."""
        self._setDataByTask(task, 8, tdir)

    def getOriginalFiles(self, task):
        """Return filename for original un-annotated image."""
        return eval(self._getDataByTask(task, 5))

    def setOriginalFiles(self, task, fnames):
        """Set the original un-annotated image filenames."""
        self._setDataByTask(task, 5, repr(fnames))

    def setAnnotatedFile(self, task, aname, pname):
        """Set the annotated image and data filenames."""
        self._setDataByTask(task, 6, aname)
        self._setDataByTask(task, 7, pname)

    def markPaperByTask(self, task, mrk, aname, pname, mtime, tdir):
        # There should be exactly one row with this Task
        r = self._findTask(task)
        # When marked, set the annotated filename, the plomfile, the mark,
        # and the total marking time (in case it was annotated earlier)
        mt = int(self.data(self.index(r, 3)))
        # total elapsed time.
        self.setData(self.index(r, 3), mtime + mt)
        self._setStatus(r, "uploading...")
        self.setData(self.index(r, 2), mrk)
        self._setAnnotatedFile(r, aname, pname)
        self._setPaperDir(r, tdir)

    def deferPaper(self, task):
        # When user defers paper, it must be unmarked or reverted already.
        # TODO: what is point of this comment?
        self.setStatusByTask(task, "deferred")

    def revertPaper(self, task):
        # When user reverts to original image, set status to "reverted"
        # mark back to -1, and marking time to zero.
        r = self._findTask(task)
        self._setStatus(r, "reverted")
        self.setData(self.index(r, 2), -1)
        self.setData(self.index(r, 3), 0)
        # Do not erase any files: could still be uploading
        self._clearPaperDir(r)

    def removePaper(self, task):
        r = self._findTask(task)
        self.removeRow(r)

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

    def getOriginalFiles(self, r):
        # Return the filename of the original un-annotated image
        return eval(self.data(self.index(r, 5)))

    def getAnnotatedFile(self, r):
        # Return the filename of the annotated image
        return self.data(self.index(r, 6))

    def rowFromTask(self, task):
        """Return the row index of this task or None if absent."""
        r0 = []
        for r in range(self.rowCount()):
            if self.getPrefix(r) == task:
                r0.append(r)

        if len(r0) == 0:
            return None
        elif not len(r0) == 1:
            raise ValueError(
                "Repeated task {} in rows {}  This should not happen!".format(task, r0)
            )
        return r0[0]


##########################


# TODO: should be a QMainWindow but at any rate not a Dialog
# TODO: should this be parented by the QApplication?
class MarkerClient(QWidget):
    my_shutdown_signal = pyqtSignal(int, list)

    def __init__(self, Qapp):
        super(MarkerClient, self).__init__()
        self.Qapp = Qapp

    def getToWork(self, mess, question, version, lastTime):

        # TODO or `self.msgr = mess`?  trouble in threads?
        global messenger
        messenger = mess
        # local temp directory for image files and the class list.
        self.workingDirectory = directoryPath
        self.question = question
        self.version = version
        # create max-mark, but not set until we get info from server
        self.maxScore = -1
        # For viewing the whole paper we'll need these two lists.
        self.viewFiles = []

        # Get the number of Tests, Pages, Questions and Versions
        try:
            self.testInfo = messenger.getInfoGeneral()
        except PlomSeriousException as err:
            self.throwSeriousError(err, rethrow=False)
            return

        # Fire up the user interface
        self.ui = Ui_MarkerWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('Plom Marker: "{}"'.format(self.testInfo["testName"]))
        # Paste the username, question and version into GUI.
        self.ui.userBox.setTitle("User: {}".format(messenger.whoami()))
        self.ui.pgLabel.setText(
            "Q{} of {}".format(str(self.question), self.testInfo["testName"])
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

        self.annotatorSettings["commentWarnings"] = lastTime.get("CommentWarnings")
        self.annotatorSettings["markWarnings"] = lastTime.get("MarkWarnings")
        self.canViewAll = False
        if lastTime.get("POWERUSER", False):
            # if POWERUSER is set, disable warnings and allow viewing all
            self.canViewAll = True
        self.allowBackgroundOps = True
        # unless special key was set:
        if lastTime.get("FOREGROUND", False):
            self.allowBackgroundOps = False

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

        # Get the max-mark for the question from the server.
        try:
            self.maxScore = messenger.MgetMaxMark(self.question, self.version)
        except PlomRangeException as err:
            log.error(err.args[1])
            ErrorMessage(err.args[1]).exec_()
            self.shutDownError()
            return
        except PlomSeriousException as err:
            self.throwSeriousError(err, rethrow=False)
            return
        # Paste the max-mark into the gui.
        self.ui.scoreLabel.setText(str(self.maxScore))

        # Get list of papers already marked and add to table.
        try:
            self.getMarkedList()
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Keep the original format around in case we need to change it
        self.ui._cachedProgressFormatStr = self.ui.mProgressBar.format()

        # Update counts
        self.updateProgress()
        # Connect the view **after** list updated.
        # Connect the table-model's selection change to appropriate function
        self.ui.tableView.selectionModel().selectionChanged.connect(self.selChanged)
        # A simple cache table for latex'd comments
        self.commentCache = {}
        self.backgroundDownloader = None
        self.backgroundUploader = None
        # Get a question to mark from the server
        self.requestNext()
        # reset the view so whole exam shown.
        self.testImg.resetB.animateClick()
        # resize the table too.
        QTimer.singleShot(100, self.ui.tableView.resizeRowsToContents)
        log.debug("Marker main thread: " + str(threading.get_ident()))
        if self.allowBackgroundOps:
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

    def throwSeriousError(self, err, rethrow=True):
        """Log an exception, pop up a dialog, shutdown.

        If you think you can do something reasonable instead of crashing pass
        False to `rethrow` and this function will initiate shutdown but will
        not re-raise the exception (this avoiding a crash).
        """
        # automatically prints a stacktrace into the log!
        log.exception("A serious error has been detected")
        msg = 'A serious error has been thrown:\n"{}"'.format(err)
        if rethrow:
            msg += "\nProbably we will crash now..."
        else:
            msg += "\nShutting down Marker."
        ErrorMessage(msg).exec_()
        self.shutDownError()
        if rethrow:
            raise(err)

    def getMarkedList(self):
        # Ask server for list of previously marked papers
        markedList = messenger.MrequestDoneTasks(self.question, self.version)
        for x in markedList:
            # TODO: might not the "markedList" have some other statuses?
            self.exM.addPaper(
                Testquestion(
                    x[0], fnames=[], stat="marked", mrk=x[2], mtime=x[3], tags=x[4]
                )
            )

    def checkAndGrabFiles(self, task):
        # TODO: doesn't seem to do a lot of checking, despite name
        if len(self.exM.getOriginalFiles(task)) > 0:
            return

        try:
            [imageList, anImage, plImage] = messenger.MrequestImages(task)
        except PlomSeriousException as e:
            self.throwSeriousError(e)
            return
        # TODO: there were no benign exceptions except authentication
        # except PlomBenignException as e:
        #     ErrorMessage("{}".format(e)).exec_()
        #     self.exM.removePaper(task)
        #     return

        paperdir = tempfile.mkdtemp(prefix=task + "_", dir=self.workingDirectory)
        log.debug("create paperdir {} for already-graded download".format(paperdir))

        # Image names = "<task>.<imagenumber>.png"
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(self.workingDirectory, "{}.{}.png".format(task, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])
        self.exM.setOriginalFiles(task, inames)

        if anImage is None:
            return

        self.exM.setPaperDirByTask(task, paperdir)
        aname = os.path.join(paperdir, "G{}.png".format(task[1:]))
        pname = os.path.join(paperdir, "G{}.plom".format(task[1:]))
        with open(aname, "wb+") as fh:
            fh.write(anImage)
        with open(pname, "wb+") as fh:
            fh.write(plImage)
        self.exM.setAnnotatedFile(task, aname, pname)

    def updateImage(self, pr=0):
        # Here the system should check if imagefiles exist and grab if needed.
        self.checkAndGrabFiles(self.prxM.getPrefix(pr))

        # Grab the group-image from file and display in the examviewwindow
        # If group has been marked then display the annotated file
        # Else display the original group image
        if self.prxM.getStatus(pr) in ("marked", "uploading...", "???"):
            self.testImg.updateImage(self.prxM.getAnnotatedFile(pr))
        else:
            self.testImg.updateImage(self.prxM.getOriginalFiles(pr))
        # wait a moment and click the reset-view button
        QTimer.singleShot(100, self.testImg.view.resetView)
        # Give focus to the table (so enter-key fires up annotator)
        self.ui.tableView.setFocus()

    def updateProgress(self, v=None, m=None):
        """Update the progress bars.

        When called with no arguments, get info from server.
        """
        if not v and not m:
            # ask server for progress update
            try:
                v, m = messenger.MprogressCount(self.question, self.version)
            except PlomSeriousException as err:
                log.exception("Serious error detected while updating progress")
                msg = 'A serious error happened while updating progress:\n"{}"'.format(err)
                msg += "\nThis is not good: restart, report bug, etc."
                ErrorMessage(msg).exec_()
                return
        if m == 0:
            v, m = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.mProgressBar.setFormat("No papers to mark")
            ErrorMessage("No papers to mark.").exec_()
        else:
            # self.ui.mProgressBar.resetFormat()
            # self.ui.mProgressBar.setFormat("%v of %m")
            # Neither is quite right, instead, we cache on init
            self.ui.mProgressBar.setFormat(self.ui._cachedProgressFormatStr)
        self.ui.mProgressBar.setMaximum(m)
        self.ui.mProgressBar.setValue(v)

    def requestNext(self):
        """Ask server for unmarked paper, get file, add to list, update view.

        Retry a view times in case two clients are asking for same.

        Side effects: on success, updates the table of tasks
        TODO: return value on success?  Currently None.
        TODO: rationalize return values
        """
        attempts = 0
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            # ask server for task of next task
            try:
                task = messenger.MaskNextTask(self.question, self.version)
                if not task:
                    return False
            except PlomSeriousException as err:
                self.throwSeriousError(err)

            try:
                imageList, tags = messenger.MclaimThisTask(task)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue

        # Image names = "<task>.<imagenumber>.png"
        inames = []
        for i in range(len(imageList)):
            tmp = os.path.join(self.workingDirectory, "{}.{}.png".format(task, i))
            inames.append(tmp)
            with open(tmp, "wb+") as fh:
                fh.write(imageList[i])

        self.exM.addPaper(Testquestion(task, inames, tags=tags))
        pr = self.prxM.rowFromTask(task)
        if pr is not None:
            # if newly-added row is visible, select it and redraw
            self.ui.tableView.selectRow(pr)
            self.updateImage(pr)
            # Clean up the table
            self.ui.tableView.resizeColumnsToContents()
            self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundStart(self):
        if self.backgroundDownloader:
            log.info(
                "Previous Downloader ({}) still here, waiting".format(
                    str(self.backgroundDownloader)
                )
            )
            # if prev downloader still going than wait.  might block the gui
            self.backgroundDownloader.wait()
        self.backgroundDownloader = BackgroundDownloader(self.question, self.version)
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

    def requestNextInBackgroundFinished(self, test, fnames, tags):
        self.exM.addPaper(Testquestion(test, fnames, tags=tags))
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

    def moveToNextUnmarkedTest(self, task):
        """Move the list to the next unmarked test, if possible.

        Return True if we moved and False if not, for any reason."""
        if self.backgroundDownloader:
            # Might need to wait for a background downloader.  Important to
            # processEvents() so we can receive the downloader-finished signal.
            # TODO: assumes the downloader tries to stay just one ahead.
            count = 0
            while self.backgroundDownloader.isRunning():
                time.sleep(0.05)
                self.Qapp.processEvents()
                count += 1
                if (count % 10) == 0:
                    log.info("waiting for downloader to fill table...")
                if count >= 100:
                    msg = SimpleMessage(
                        "Still waiting for downloader to get the next image.  "
                        "Do you want to wait a few more seconds?\n\n"
                        "(It is safe to choose 'no': the Annotator will simply close)"
                    )
                    if msg.exec_() == QMessageBox.No:
                        return False
                    count = 0
            self.Qapp.processEvents()

        # Move to the next unmarked test in the table.
        # Be careful not to get stuck in a loop if all marked
        prt = self.prxM.rowCount()
        if prt == 0:
            return False
        # get current position from the tgv
        prstart = self.prxM.rowFromTask(task)

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
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        # If test does not have status "marked" then nothing to do.  Could
        # check `backgroundUploader.isEmpty()` but this simple status check
        # should prevent reverting while upload is in progress.
        if self.exM.getStatusByTask(task) != "marked":
            return
        # Check user really wants to revert
        msg = SimpleMessage("Do you want to revert to original scan?")
        if msg.exec_() == QMessageBox.No:
            return
        # send revert message to server
        messenger.MrevertTask(task)
        # Revert the test in the table (set status, mark etc)
        self.exM.revertPaper(task)
        # Update the image (is now back to original untouched image)
        self.updateImage(pr)
        self.updateProgress()

    def deferTest(self):
        """Mark test as "defer" - to be skipped until later."""
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        if self.exM.getStatusByTask(task) == "deferred":
            return
        if self.exM.getStatusByTask(task) in ("marked", "uploading...", "???"):
            msg = ErrorMessage("Paper is already marked - revert it before deferring.")
            msg.exec_()
            return
        self.exM.deferPaper(task)

    def startTheAnnotator(self, task, paperdir, fnames, saveName, pname=None):
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

        if self.allowBackgroundOps:
            # while annotator is firing up request next paper in background
            # after giving system a moment to do `annotator.exec_()`
            if self.exM.countReadyToMark() == 0:
                self.requestNextInBackgroundStart()
        # build the annotator - pass it the image filename, the max-mark
        # the markingstyle (up/down/total) and mouse-hand (left/right)
        annotator = Annotator(
            task,
            self.testInfo["testName"],
            paperdir,
            fnames,
            saveName,
            self.maxScore,
            markStyle,
            mouseHand,
            parent=self,
            plomDict=pdict,
        )
        # run the annotator
        annotator.ann_upload.connect(self.callbackAnnWantsUsToUpload)
        annotator.ann_done_wants_more.connect(self.callbackAnnDoneWantsMore)
        annotator.ann_done_closing.connect(self.callbackAnnDoneClosing)
        annotator.ann_done_reject.connect(self.callbackAnnDoneCancel)
        self.setEnabled(False)
        annotator.show()
        # We had (have?) a bug: when `annotator` var goes out of scope, it can
        # get GC'd, killing the new Annotator.  Fix: keep a ref in self.
        # TODO: the old one might still be closing when we get here, but dropping
        # the ref now won't hurt (I think).
        self._annotator = annotator

    def annotateTest(self):
        """Grab current test from table, do checks, start annotator."""
        if len(self.ui.tableView.selectedIndexes()):
            row = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(row)
        # split fcn: maybe we want to start the annotator not based on current selection
        self.annotateTest_doit(task)

    def annotateTest_doit(self, task):
        """Start annotator on a particular task."""
        # Create annotated filename. If original mXXXXgYY, then
        # annotated version is GXXXXgYY (G=graded).
        assert task.startswith("m")
        Gtask = "G" + task[1:]
        paperdir = tempfile.mkdtemp(prefix=task[1:] + "_", dir=self.workingDirectory)
        log.debug("create paperdir {} for annotating".format(paperdir))
        aname = os.path.join(paperdir, Gtask + ".png")
        cname = os.path.join(paperdir, Gtask + ".json")
        pname = os.path.join(paperdir, Gtask + ".plom")

        # If image has been marked confirm with user if they want
        # to annotate further.
        remarkFlag = False

        if self.exM.getStatusByTask(task) in ("marked", "uploading...", "???"):
            msg = SimpleMessage("Continue marking paper?")
            if not msg.exec_() == QMessageBox.Yes:
                return
            remarkFlag = True
            oldpaperdir = self.exM.getPaperDirByTask(task)
            log.debug("oldpaperdir is " + oldpaperdir)
            assert oldpaperdir is not None
            oldaname = os.path.join(oldpaperdir, Gtask + ".png")
            oldpname = os.path.join(oldpaperdir, Gtask + ".plom")
            # oldcname = os.path.join(oldpaperdir, Gtask + ".json")
            # TODO: json file not downloaded
            # https://gitlab.math.ubc.ca/andrewr/MLP/issues/415
            shutil.copyfile(oldaname, aname)
            shutil.copyfile(oldpname, pname)
            # shutil.copyfile(oldcname, cname)

        # Yes do this even for a regrade!  We will recreate the annotations
        # (using the plom file) on top of the original file.
        fnames = self.exM.getOriginalFiles(task)
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
                    log.info("waiting for downloader: {}".format(fnames))
                if count >= 40:
                    msg = SimpleMessage(
                        "Still waiting for download.  Do you want to wait a bit longer?"
                    )
                    if msg.exec_() == QMessageBox.No:
                        return
                    count = 0

        # maybe the downloader failed for some (rare) reason
        for fn in fnames:
            if not os.path.exists(fn):
                log.warning(
                    "some kind of downloader fail? (unexpected, but probably harmless"
                )
                return

        # stash the previous state, not ideal because makes column wider
        prevState = self.exM.getStatusByTask(task)
        self.exM.setStatusByTask(task, "ann:" + prevState)

        if remarkFlag:
            self.startTheAnnotator(task[1:], paperdir, fnames, aname, pname)
        else:
            self.startTheAnnotator(task[1:], paperdir, fnames, aname, None)
        # we started the annotator, we'll get a signal back when its done

    # when Annotator done, we come back to one of these callbackAnnDone* fcns
    @pyqtSlot(str)
    def callbackAnnDoneCancel(self, task):
        self.setEnabled(True)
        prevState = self.exM.getStatusByTask("m" + task).split(":")[-1]
        # TODO: could also erase the paperdir
        self.exM.setStatusByTask("m" + task, prevState)

    @pyqtSlot(str)
    def callbackAnnDoneClosing(self, task):
        self.setEnabled(True)
        # update image view, if the row we just finished is selected
        prIndex = self.ui.tableView.selectedIndexes()
        if len(prIndex) == 0:
            return
        pr = prIndex[0].row()
        if self.prxM.getPrefix(pr) == "m" + task:
            self.updateImage(pr)

    @pyqtSlot(str)
    def callbackAnnDoneWantsMore(self, task):
        log.debug("Marker is back and Ann Wants More")
        if not self.allowBackgroundOps:
            self.requestNext()
        if self.moveToNextUnmarkedTest("m" + task):
            self.annotateTest()
        else:
            log.debug("either we are done or problems downloading...")
            self.setEnabled(True)

    @pyqtSlot(str, list)
    def callbackAnnWantsUsToUpload(self, task, stuff):
        gr, mtime, paperdir, fnames, aname, pname, cname = stuff

        if not (0 <= gr and gr <= self.maxScore):
            msg = ErrorMessage(
                "Mark of {} is outside allowed range. Rejecting. This should not happen. Please file a bug".format(gr)
            )
            msg.exec_()
            # TODO: what do do here?  revert?
            return

        # Copy the mark, annotated filename and the markingtime into the table
        # TODO: sort this out whether task is "m00..." or "00..."?!
        self.exM.markPaperByTask("m" + task, gr, aname, pname, mtime, paperdir)
        # update the mtime to be the total marking time
        totmtime = self.exM.getMTimeByTask("m" + task)
        tags = self.exM.getTagsByTask("m" + task)

        _data = (
            "m" + task,  # current task
            gr,  # grade
            (aname, pname, cname),  # annotated, plom, and comment filenames
            totmtime,  # total marking time
            self.question,
            self.version,
            tags,
        )
        if self.allowBackgroundOps:
            # the actual upload will happen in another thread
            self.backgroundUploader.enqueueNewUpload(*_data)
        else:
            upload(
                *_data,
                failcallback=self.backgroundUploadFailed,
                successcallback=self.backgroundUploadFinished
            )

    def backgroundUploadFinished(self, code, numdone, numtotal):
        """An upload has finished, do appropriate UI updates"""
        stat = self.exM.getStatusByTask(code)
        # maybe it changed while we waited for the upload
        if stat == "uploading...":
            self.exM.setStatusByTask(code, "marked")
        self.updateProgress(numdone, numtotal)

    def backgroundUploadFailed(self, code, errmsg):
        """An upload has failed, not sure what to do but do to it LOADLY"""
        self.exM.setStatusByTask(code, "???")
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
        log.error("shutting down")
        self.my_shutdown_signal.emit(2, [])
        self.close()

    def shutDown(self):
        log.debug("Marker shutdown from thread " + str(threading.get_ident()))
        if self.backgroundUploader:
            count = 42
            while self.backgroundUploader.isRunning():
                if self.backgroundUploader.isEmpty():
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

    def downloadWholePaper(self, testNumber):
        try:
            pageNames, imagesAsBytes = messenger.MrequestWholePaper(testNumber)
        except PlomTakenException as err:
            log.exception("Taken exception when downloading whole paper")
            ErrorMessage("{}".format(err)).exec_()
            return ([], [])   # TODO: what to return?

        viewFiles = []
        for iab in imagesAsBytes:
            tfn = tempfile.NamedTemporaryFile(
                dir=self.workingDirectory, suffix=".png", delete=False
            ).name
            viewFiles.append(tfn)
            with open(tfn, "wb") as fh:
                fh.write(iab)

        return [pageNames, viewFiles]

    def doneWithWholePaperFiles(self, viewFiles):
        for f in viewFiles:
            if os.path.isfile(f):
                os.unlink(f)

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
        n = int(self.question)
        testname = self.testInfo["testName"]

        for X in clist:
            if commentIsVisible(X, n, testname) and X["text"][:4].upper() == "TEX:":
                txt = X["text"][4:].strip()
                pd.setLabelText("Caching:\n{}".format(txt[:64]))
                # latex the red version
                self.latexAFragment(txt)
                c += 1
                pd.setValue(c)
                # and latex the preview
                txtp = "\\color{blue}" + txt  # make color blue for ghost rendering
                self.latexAFragment(txtp)
                c += 1
                pd.setValue(c)
            else:
                c += 2
                pd.setValue(c)

    def latexAFragment(self, txt):
        """Run LaTeX on a fragment of text and return the file name of a png.

        The files are cached for reuse if the same text is passed again.
        """
        if txt in self.commentCache:
            # have already latex'd this comment
            return self.commentCache[txt]
        log.debug('requesting latex for "{}"'.format(txt))
        try:
            fragment = messenger.MlatexFragment(txt)
        except PlomLatexException:
            return None
        # a name for the fragment file
        fragFile = tempfile.NamedTemporaryFile(
            dir=self.workingDirectory, suffix=".png", delete=False
        ).name
        # save it
        with open(fragFile, "wb+") as fh:
            fh.write(fragment)
        # add it to the cache
        self.commentCache[txt] = fragFile
        return fragFile

    def tagTest(self):
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        tagSet = self.exM.getAllTags()
        currentTag = self.exM.getTagsByTask(task)

        atb = AddTagBox(self, currentTag, list(tagSet))
        if atb.exec_() == QDialog.Accepted:
            txt = atb.TE.toPlainText().strip()
            # truncate at 256 characters.  TODO: without warning?
            if len(txt) > 256:
                txt = txt[:256]

            self.exM.setTagsByTask(task, txt)
            # resize view too
            self.ui.tableView.resizeRowsToContents()

            # send updated tag back to server.
            try:
                messenger.MsetTag(task, txt)
            except PlomTakenException as err:
                log.exception("exception when trying to set tag")
                ErrorMessage('Could not set tag:\n"{}"'.format(err)).exec_()
            except PlomSeriousException as err:
                self.throwSeriousError(err)
        return

    def setFilter(self):
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        self.prxM.filterTags()

    def viewSpecificImage(self):
        if self.canViewAll:
            tgs = SelectTestQuestion(self.testInfo, self.question)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = tgs.gsb.value()
            else:
                return
        else:
            tgs = SelectTestQuestion(self.testInfo)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = self.question
            else:
                return
        task = "m{}g{}".format(str(tn).zfill(4), int(self.question))
        try:
            imageList = messenger.MrequestOriginalImages(task)
        except PlomNoMoreException as err:
            msg = ErrorMessage("No image corresponding to code {}".format(task))
            msg.exec_()
            return
        ifilenames = []
        for img in imageList:
            ifile = tempfile.NamedTemporaryFile(
                dir=self.workingDirectory, suffix=".png", delete=False
            )
            ifile.write(img)
            ifilenames.append(ifile.name)
        tvw = GroupView(ifilenames)
        tvw.setWindowTitle(
            "Original ungraded image for question {} of test {}".format(gn, tn)
        )
        tvw.exec_()
