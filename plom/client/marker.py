# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

"""
The Plom Marker client
"""

__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Elvis Cai", "Colin Macdonald", "Victoria Schuster"]
__license__ = "AGPL-3.0-or-later"


import json
import logging
import os
import secrets
import io

# in order to get shortcuts under OSX this needs to set this.... but only osx.
# To test platform
import platform
import queue
import shutil
import tempfile
import threading
import time
from collections import defaultdict

from PyQt5.QtCore import (
    Qt,
    QSortFilterProxyModel,
    QTimer,
    QThread,
    pyqtSlot,
    pyqtSignal,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from plom.plom_exceptions import (
    PlomRangeException,
    PlomSeriousException,
    PlomTakenException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
    PlomConflict,
    PlomException,
    PlomLatexException,
    PlomNoMoreException,
)
from plom.messenger import Messenger
from .annotator import Annotator
from .comment_list import AddTagBox, commentLoadAll, commentIsVisible
from .examviewwindow import ExamViewWindow
from .origscanviewer import GroupView, SelectTestQuestion
from .uiFiles.ui_marker import Ui_MarkerWindow
from .useful_classes import ErrorMessage, SimpleMessage

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
    """
    Downloads exams in background.

    Notes:
        Read https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
        and https://stackoverflow.com/questions/6783194/background-thread-with-qthread-in-pyqt
        and finally https://woboq.com/blog/qthread-you-were-not-doing-so-wrong.html
        (Done in the simpler subclassing way.)

    """

    downloadSuccess = pyqtSignal(str, list, str, str)
    downloadNoneAvailable = pyqtSignal()
    downloadFail = pyqtSignal(str)

    def __init__(self, question, version, msgr_clone):
        """
        Initializes a new downloader.

        Args:
            question (str): question number
            version (str): version number.
            msgr_clone (Messenger): use this for the actual downloads.
                Note Messenger is not multithreaded and blocks using
                mutexes, so you may want to pass a clone of your
                Messenger, rather than the one you are using youself!

        Notes:
            question/version may be able to be type int as well.
        """
        super().__init__()
        self.question = question
        self.version = version
        self.workingDirectory = directoryPath
        self._msgr = msgr_clone

    def run(self):
        """
        Runs the background downloader.

        Notes:
            Overrides run method of QThread.

        Returns:
            None

        """
        attempts = 0
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            # ask server for task-code of next task
            try:
                log.debug("bgdownloader: about to download")
                task = self._msgr.MaskNextTask(self.question, self.version)
                if not task:  # no more tests left
                    self.downloadNoneAvailable.emit()
                    self.quit()
                    return
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()
                return

            try:
                page_metadata, tags, integrity_check = self._msgr.MclaimThisTask(task)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

        # TODO: hardcoding orientation to 0, Issue #1306
        src_img_data = [{"md5": x[1], "orientation": 0} for x in page_metadata]
        # Image names = "<task>.<imagenumber>.<extension>"
        for i, row in enumerate(page_metadata):
            # try-except? how does this fail?
            im_bytes = self._msgr.MrequestOneImage(task, row[0], row[1])
            tmp = os.path.join(self.workingDirectory, "{}.{}.image".format(task, i))
            src_img_data[i]["filename"] = tmp
            with open(tmp, "wb+") as fh:
                fh.write(im_bytes)
        self.downloadSuccess.emit(task, src_img_data, tags, integrity_check)
        self.quit()


class BackgroundUploader(QThread):
    """Uploads exams in Background."""

    uploadSuccess = pyqtSignal(str, int, int)
    uploadKnownFail = pyqtSignal(str, str)
    uploadUnknownFail = pyqtSignal(str, str)

    def __init__(self, msgr):
        """Initialize a new uploader

        args:
            msgr (Messenger):
                Note Messenger is not multithreaded and blocks using
                mutexes.  Here we make our own private clone so caller
                can keep using their's.
                TODO: have caller do clone, for symmetry with downloader?
        """
        super().__init__()
        self._msgr = Messenger.clone(msgr)

    def enqueueNewUpload(self, *args):
        """
        Places something in the upload queue.

        Note:
            If you call this from the main thread, this code runs in the
            main thread. That is ok because Queue is threadsafe, but it's
            important to be aware, not all code in this object runs in the new
            thread: it depends on where that code is called!

        Args:
            *args: all input arguments are cached and will eventually be
                passed untouched to the `upload` function.  There is one
                exception: `args[0]` is assumed to contain the task str
                of the form `"q1234g9"` for printing debugging messages.

        Returns:
            None
        """
        log.debug("upQ enqueing item from main thread " + str(threading.get_ident()))
        self.q.put(args)

    def isEmpty(self):
        """
        Checks if the upload queue is empty.

        Returns:
            True if the upload queue is empty, false otherwise.

        """
        return self.q.empty()

    def run(self):
        """
        Runs the uploader in background.

        Notes:
            Overrides run method of Qthread.

        Returns:
            None

        """

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
                self._msgr,
                *data,
                knownFailCallback=self.uploadKnownFail.emit,
                unknownFailCallback=self.uploadUnknownFail.emit,
                successCallback=self.uploadSuccess.emit,
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
    _msgr,
    task,
    grade,
    filenames,
    mtime,
    question,
    ver,
    tags,
    integrity_check,
    image_md5_list,
    knownFailCallback=None,
    unknownFailCallback=None,
    successCallback=None,
):
    """
    Uploads a paper.

    Args:
        task (str): the Task ID for the page being uploaded. Takes the form
            "q1234g9" = test 1234 question 9.
        grade (int): grade given to question.
        filenames (list[str]): a list containing the annotated file's name,
            the .plom file's name and the comment file's name, in that order.
        mtime (int): the marking time (s) for this specific question.
        question (int or str): the question number
        ver (int or str): the version number
        tags (str): any tags associated with this exam.
        integrity_check (str): the integrity_check string of the task.
        image_md5_list (list[str]): a list of image md5sums used.
        knownFailCallback: if we fail in a way that is reasonably expected,
            call this function.
        unknownFailCallback: if we fail but don't really know why or what
            do to, call this function.
        successCallback: a function to call when we succeed.

    Returns:
        None

    Raises:
        PlomSeriousException if elements in filenames do not correspond to
            the same exam.

    """
    # do name sanity checks here
    aname, pname, cname = filenames

    if not (
        task.startswith("q")
        and os.path.basename(aname) == "G{}.png".format(task[1:])
        and os.path.basename(pname) == "G{}.plom".format(task[1:])
        and os.path.basename(cname) == "G{}.json".format(task[1:])
    ):
        raise PlomSeriousException(
            "Upload file names mismatch [{}, {}, {}] - this should not happen".format(
                aname, pname, cname
            )
        )
    try:
        msg = _msgr.MreturnMarkedTask(
            task,
            question,
            ver,
            grade,
            mtime,
            tags,
            aname,
            pname,
            cname,
            integrity_check,
            image_md5_list,
        )
    except (PlomTaskChangedError, PlomTaskDeletedError, PlomConflict) as ex:
        knownFailCallback(task, str(ex))
        # probably previous call does not return: it forces a crash
        return
    except PlomException as ex:
        unknownFailCallback(task, str(ex))
        return

    numDone = msg[0]
    numTotal = msg[1]
    successCallback(task, numDone, numTotal)


class ExamQuestion:
    """
    A class storing identifying information for one Exam Question.

    A simple container for storing a groupimage's task ID,
    numer, group, version, status, the mark, the original image
    filename, the annotated image filename, the mark, and the
    time spent marking the groupimage.
    """

    def __init__(
        self,
        task,
        *,
        src_img_data=[],
        stat="untouched",
        mrk="-1",
        mtime="0",
        tags="",
        integrity_check="",
    ):
        """
        Initializes an exam question.

        Args:
            task (str): the Task ID for the page being uploaded. Takes the form
            "q1234g9" = test 1234 question 9.
            stat (str): test status.
            mrk (int): the mark of the question.
            mtime (int): marking time spent on that page in seconds.
            tags (str): Tags corresponding to the exam.
            integrity_check (str): integrity_check = concat of md5sums of underlying images
            src_img_metadata (list[dict]): a list of dicts of md5sums,
                filenames and other metadata of the images for the test
                question.

        Notes:
            By default set mark to be negative (since 0 is a possible mark)
        """
        self.prefix = task
        self.status = stat
        self.mark = mrk
        self.src_img_data = src_img_data
        self.annotatedFile = ""  # The filename for the (future) annotated image
        self.plomFile = ""  # The filename for the (future) plom file
        self.markingTime = mtime
        self.tags = tags
        self.integrity_check = integrity_check


class MarkerExamModel(QStandardItemModel):
    """A tablemodel for handling the group image marking data."""

    def __init__(self, parent=None):
        """
        Initializes a new MarkerExamModel.

        Args:
            parent (QStandardItemModel): MarkerExamModel's Parent.

        """
        QStandardItemModel.__init__(self, parent)
        self.setHorizontalHeaderLabels(
            [
                "Task",
                "Status",
                "Mark",
                "Time (s)",
                "Tag",
                "OriginalFiles",
                "AnnotatedFile",
                "PlomFile",
                "PaperDir",
                "integrity_check",
                "src_img_data",
            ]
        )

    def addPaper(self, paper):
        """
        Adds a paper to self.

        Args:
            paper (ExamQuestion): the paper to be added

        Returns:
            r (int): the row identifier of the added paper.

        """
        # check if paper is already in model - if so, delete it and add it back with the new data.
        # **but** be careful - if annotation in progress then ??
        try:
            r = self._findTask(paper.prefix)
        except ValueError:
            pass
        else:
            ErrorMessage(
                "Task {} has been modified by server - you will need to annotate it again.".format(
                    paper.prefix
                )
            ).exec_()
            self.removeRow(r)
        # Append new groupimage to list and append new row to table.
        r = self.rowCount()
        self.appendRow(
            [
                QStandardItem(paper.prefix),
                QStandardItem(paper.status),
                QStandardItem(str(paper.mark)),
                QStandardItem(str(paper.markingTime)),
                QStandardItem(paper.tags),
                QStandardItem("placeholder"),
                QStandardItem(paper.annotatedFile),
                QStandardItem(paper.plomFile),
                QStandardItem("placeholder"),
                # todo - reorder these?
                QStandardItem(paper.integrity_check),
                QStandardItem(repr(paper.src_img_data)),
            ]
        )
        return r

    def _getPrefix(self, r):
        """
        Return the prefix of the image

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the prefix of the image

        """
        return self.data(self.index(r, 0))

    def _getStatus(self, r):
        """
        Returns the status of the image.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the status of the image

        """
        return self.data(self.index(r, 1))

    def _setStatus(self, r, stat):
        """
        Sets the status of the image.

        Args:
            r (int): the row identifier of the paper.
            stat (str): the new status of the image.

        Returns:
            None

        """
        self.setData(self.index(r, 1), stat)

    def _getAnnotatedFile(self, r):
        """
        Returns the filename of the annotated image.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the filename of the annotated image

        """
        return self.data(self.index(r, 6))

    def _setAnnotatedFile(self, r, aname, pname):
        """
        Set the file name for the annotated image.

        Args:
            r (int): the row identifier of the paper.
            aname (str): the name for the annotated file.
            pname (str): the name for the .plom file

        Returns:
            None

        """
        self.setData(self.index(r, 6), aname)
        self.setData(self.index(r, 7), pname)

    def _setPaperDir(self, r, tdir):
        """
        Sets the paper directory for the given paper.
        Args:
            r (int): the row identifier of the paper.
            tdir (dir): a temporary directory for this paper.

        Returns:
            None
        """
        self.setData(self.index(r, 8), tdir)

    def _clearPaperDir(self, r):
        """
        Clears the paper directory for the given paper.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            None
        """
        self._setPaperDir(r, None)

    def _getPaperDir(self, r):
        """
        Returns the paper directory for the given paper.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (dir): a temporary directory for this paper.
        """
        return self.data(self.index(r, 8))

    def _findTask(self, task):
        """
        Return the row index of this task.

        Args:
            task (str): the task for the image files to be loaded from.
                Takes the form "q1234g9" = test 1234 question 9

        Raises:
             ValueError if not found.
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
        """
        Find the row identifier with `task` and sets `n`th column to `stuff`.

        Args:
            task (str): the task for the image files to be loaded from.
            n (int): the column to be loaded into.
            stuff: whatever is being added.

        Returns:
            None
        """
        r = self._findTask(task)
        self.setData(self.index(r, n), stuff)

    def _getDataByTask(self, task, n):
        """
        Returns contents of task in `n`th column.

        Args:
            task (str): the task for the image files to be loaded from.
            n (int): the column to return from.

        Returns:
            Contents of task in `n`th column.
        """
        r = self._findTask(task)
        return self.data(self.index(r, n))

    def getStatusByTask(self, task):
        """Return status for task (task(str) defined above.)"""
        return self._getDataByTask(task, 1)

    def setStatusByTask(self, task, st):
        """Set status for task, ((task(str) and st(str) defined above.)"""
        self._setDataByTask(task, 1, st)

    def getTagsByTask(self, task):
        """Return tags for task, (task(str) defined above.)"""
        return self._getDataByTask(task, 4)

    def setTagsByTask(self, task, tags):
        """Set tags for task, (task (str) defined above.)"""
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
        """Return total marking time (s) for task, (task(str), return (int).)"""
        return int(self._getDataByTask(task, 3))

    def getPaperDirByTask(self, task):
        """Return temporary directory for this task, (task(str) defined above)"""
        return self._getDataByTask(task, 8)

    def setPaperDirByTask(self, task, tdir):
        """
        Set temporary directory for this grading.

        Args:
            task (str): the task for the image files to be loaded from.
            tdir (dir): the temporary directory for task to be set to.

        Returns:
            None
        """
        self._setDataByTask(task, 8, tdir)

    def getOriginalFiles(self, task):
        """Return filenames for original un-annotated image as string.

        Somewhat deprecated?
        """
        src_img_data = self.get_source_image_data(task)
        return [x["filename"] for x in src_img_data]

    def _setImageData(self, task, src_img_data):
        """Set the md5sums etc of the original image files."""
        log.debug("Setting img data to {}".format(src_img_data))
        self._setDataByTask(task, 10, repr(src_img_data))

    def get_source_image_data(self, task):
        """Return the image data (as a list of dicts) for task."""
        # dangerous repr/eval pair?  Is json safer/better?
        r = eval(self._getDataByTask(task, 10))
        return r

    def setOriginalFilesAndData(self, task, src_img_data):
        """Set the original un-annotated image filenames and other metadata."""
        self._setImageData(task, src_img_data)

    def setAnnotatedFile(self, task, aname, pname):
        """Set the annotated image and .plom file names."""
        self._setDataByTask(task, 6, aname)
        self._setDataByTask(task, 7, pname)

    def getIntegrityCheck(self, task):
        """Return integrity_check for task as string."""
        return self._getDataByTask(task, 9)

    def markPaperByTask(self, task, mrk, aname, pname, mtime, tdir):
        """
        Add marking data for the given task.

        Args:
            task (str): the task for the image files to be loaded from.
            mrk (int): the mark for this paper.
            aname (str): the annotated file name.
            pname (str): the .plom file name.
            mtime (int): total marking time in seconds.
            tdir (dir): the temporary directory for task to be set to.

        Returns:
            None

        """
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
        """ Sets the status for the task's paper to deferred. """
        self.setStatusByTask(task, "deferred")

    def removePaper(self, task):
        """ Removes the task's paper from self."""
        r = self._findTask(task)
        self.removeRow(r)

    def countReadyToMark(self):
        """Returns the number of untouched Papers."""
        count = 0
        for r in range(self.rowCount()):
            if self._getStatus(r) == "untouched":
                count += 1
        return count


##########################
class ProxyModel(QSortFilterProxyModel):
    """A proxymodel wrapper to handle filtering and sorting of table model."""

    def __init__(self, parent=None):
        """
        Initializes a new ProxyModel object.

        Args:
            parent (QObject): self's parent.
        """
        QSortFilterProxyModel.__init__(self, parent)
        self.setFilterKeyColumn(4)
        self.filterString = ""
        self.invert = False

    def lessThan(self, left, right):
        """
        Sees if left data is less than right data.

        Args:
            left (QModelIndex): the left map.
            right (QModelIndex):

        Returns:
            True if left data is less than right data.

        """
        # Check to see if data is integer, and compare that
        try:
            lv = int(left.data())
            rv = int(right.data())
            return lv < rv
        except ValueError:
            # else let qt handle it.
            return left.data() < right.data()

    def setFilterString(self, flt):
        """
        Sets the Filter String.

        Args:
            flt (str): the string to filter by

        Returns:
            None

        """
        self.filterString = flt

    def filterTags(self, invert=False):
        """
        Sets the Filter Tags based on string.

        Args:
            invert (bool): True if looking for files that do not have given
                filter string, false otherwise.

        Returns:
            None

        """
        self.invert = invert
        self.setFilterFixedString(self.filterString)

    def filterAcceptsRow(self, pos, index):
        """
        Checks if a row fits the given filter.

        Notes:
            Overrides base method.

        Args:
            pos (int): row desired.
            index (any): unused.

        Returns:
            True if filter accepts the row, False otherwise.

        """
        if (len(self.filterString) == 0) or (
            self.filterString.casefold()
            in self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
        ):
            # we'd return true here, unless INVERT, then false
            if self.invert:
                return False
            else:
                return True
        else:  # we'd return false here, unless invert, then true
            if self.invert:
                return True
            else:
                return False

    def getPrefix(self, r):
        """
        Returns the task code of inputted row index.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the prefix of the paper indicated by r.

        """
        return self.data(self.index(r, 0))

    def getStatus(self, r):
        """
        Returns the status of inputted row index.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the status of the paper indicated by r.

        """
        # Return the status of the image
        return self.data(self.index(r, 1))

    def getAnnotatedFile(self, r):
        """
        Returns the file names of the annotated image of r.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            (str): the file name of the annotated image of the paper in r.

        """
        return self.data(self.index(r, 6))

    def rowFromTask(self, task):
        """Return the row index (int) of this task (str) or None if absent."""
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


class MarkerClient(QWidget):
    """
    Setup for marking client and annotator

    Notes:
        TODO: should be a QMainWindow but at any rate not a Dialog
        TODO: should this be parented by the QApplication?
    """

    my_shutdown_signal = pyqtSignal(int, list)

    def __init__(self, Qapp):
        """
        Initialize a new MarkerClient

        Args:
            Qapp(QApplication): Main client application

        """
        super().__init__()
        self.Qapp = Qapp

        # instance vars we can initialize now
        self.workingDirectory = (
            directoryPath
            # local temp directory for image files and the class list.
        )
        self.viewFiles = []  # For viewing the whole paper we'll need these two lists.
        self.maxMark = -1  # temp value
        self.examModel = (
            MarkerExamModel()
        )  # Exam model for the table of groupimages - connect to table
        self.prxM = ProxyModel()  # set proxy for filtering and sorting
        self.testImg = (
            ExamViewWindow()
        )  # A view window for the papers so user can zoom in as needed.
        self.annotatorSettings = defaultdict(
            lambda: None
        )  # settings variable for annotator settings (initially None)
        self.commentCache = {}  # cache for Latex Comments
        self.backgroundDownloader = None
        self.backgroundUploader = None

        self.allowBackgroundOps = True
        self.canViewAll = False

        # instance vars that get initialized later
        self.question = None
        self.version = None
        self.exam_spec = None
        self.ui = None
        self.canViewAll = None

    def setup(self, markerMessenger, question, version, lastTime):
        """
        Performs setup procedure for markerClient.

        TODO: Change the __init__ params to include the
            params below and move this method into init

        TODO: verify all lastTime Params, there are almost certainly some missing

        Args:
            markerMessenger (Messenger): messenger client for communicating with server
            question (int): question number.
            version (int): version number
            lastTime (dict): a dictionary containing
                 {"user": username
                "server": serverNumber
                 "question": question number
                 "version": version number
                 "fontsize"
                 "POWERUSER"
                 "FOREGROUND"
                 "upDown": marking style (up vs down)
                 "LogLevel"
                 "LogToFile"
                 "CommentsWarnings"
                 "MarkWarnings"
                 "mouse": left or right mouse hand
                 "SidebarOnRight": True if sidebar is on right
                  }
                and potentially others

        Returns:
            None
        """
        self.msgr = markerMessenger
        # BackgroundDownloaders come and go but share a single cloned Messenger
        # Note: BackgroundUploader is persistent and makes its own clone.
        self._bgdownloader_msgr = Messenger.clone(self.msgr)
        self.question = question
        self.version = version

        # Get the number of Tests, Pages, Questions and Versions
        try:
            self.exam_spec = self.msgr.get_spec()
        except PlomSeriousException as err:
            self.throwSeriousError(err, rethrow=False)
            return

        self.UIInitialization()
        self.applyLastTimeOptions(lastTime)
        self.connectGuiButtons()
        self.setMarkStyleID()

        if not self.getMaxMark():  # indicates exception was caught
            return
        self.ui.maxscoreLabel.setText(str(self.maxMark))

        try:
            self.loadMarkedList()  # Get list of papers already marked and add to table.
        except PlomSeriousException as err:
            self.throwSeriousError(err)
            return

        # Keep the original format around in case we need to change it
        self.ui._cachedProgressFormatStr = self.ui.mProgressBar.format()
        self.updateProgress()  # Update counts

        # Connect the view **after** list updated.
        # Connect the table-model's selection change to appropriate function
        self.ui.tableView.selectionModel().selectionChanged.connect(self.updateImg)

        self.requestNext()  # Get a question to mark from the server
        self.testImg.resetB.animateClick()  # reset the view so whole exam shown.
        # resize the table too.
        QTimer.singleShot(100, self.ui.tableView.resizeRowsToContents)
        log.debug("Marker main thread: " + str(threading.get_ident()))

        if self.allowBackgroundOps:
            self.backgroundUploader = BackgroundUploader(self.msgr)
            self.backgroundUploader.uploadSuccess.connect(self.backgroundUploadFinished)
            self.backgroundUploader.uploadKnownFail.connect(
                self.backgroundUploadFailedServerChanged
            )
            self.backgroundUploader.uploadUnknownFail.connect(
                self.backgroundUploadFailed
            )
            self.backgroundUploader.start()
        self.cacheLatexComments()  # Now cache latex for comments:

    def applyLastTimeOptions(self, lastTime):
        """
        Applies all settings from previous client.

        Args:
            lastTime (dict): a dictionary containing information
                            for prev client. See setup for more info.

        Returns:
            None
        """
        self.annotatorSettings["commentWarnings"] = lastTime.get("CommentWarnings")
        self.annotatorSettings["markWarnings"] = lastTime.get("MarkWarnings")

        if lastTime.get("POWERUSER", False):
            # if POWERUSER is set, disable warnings and allow viewing all
            self.canViewAll = True

        if lastTime.get("FOREGROUND", False):
            self.allowBackgroundOps = False

        self.ui.sidebarRightCB.setChecked(lastTime.get("SidebarOnRight", False))

        if lastTime["upDown"] == "up":
            self.ui.markUpRB.animateClick()

        elif lastTime["upDown"] == "down":
            self.ui.markDownRB.animateClick()

        if lastTime["mouse"] == "left":
            self.ui.leftMouseCB.setChecked(True)

    def UIInitialization(self):
        """
        Startup procedure for the user interface

        Returns:
            None: Modifies self.ui

        """
        # Fire up the user interface
        self.ui = Ui_MarkerWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('Plom Marker: "{}"'.format(self.exam_spec["name"]))
        # Paste the username, question and version into GUI.
        self.ui.userLabel.setText(self.msgr.whoami())
        self.ui.infoBox.setTitle(
            "Marking Q{} (ver. {}) of “{}”".format(
                self.question, self.version, self.exam_spec["name"]
            )
        )

        self.prxM.setSourceModel(self.examModel)
        self.ui.tableView.setModel(self.prxM)
        # hide various columns without end-user useful info
        self.ui.tableView.hideColumn(5)
        self.ui.tableView.hideColumn(6)
        self.ui.tableView.hideColumn(7)
        self.ui.tableView.hideColumn(8)
        self.ui.tableView.hideColumn(9)
        # TODO: temporarily shown for debugging
        # self.ui.tableView.hideColumn(10)

        # Double-click or signal fires up the annotator window
        self.ui.tableView.doubleClicked.connect(self.annotateTest)
        self.ui.tableView.annotateSignal.connect(self.annotateTest)
        # A view window for the papers so user can zoom in as needed.
        # Paste into appropriate location in gui.
        self.ui.gridLayout_6.addWidget(self.testImg, 0, 0)

    def connectGuiButtons(self):
        """
        Connect gui buttons to appropriate functions

        Notes:
            TODO: remove the total-radiobutton

        Returns:
            None - Modifies self.ui
        """
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.deferButton.clicked.connect(self.deferTest)
        self.ui.tagButton.clicked.connect(self.tagTest)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        self.ui.filterInvCB.stateChanged.connect(self.setFilter)
        self.ui.viewButton.clicked.connect(self.viewSpecificImage)

    def getMaxMark(self):
        """
        Get the max-mark for the question from the server.

        Returns
            True if max score retrieved successfully, False otherwise
        """
        try:
            self.maxMark = self.msgr.MgetMaxMark(self.question, self.version)
        except PlomRangeException as err:
            log.error(err)
            ErrorMessage(str(err)).exec_()
            self.shutDownError()
            return False
        except PlomSeriousException as err:
            self.throwSeriousError(err, rethrow=False)
            return False
        return True

    def setMarkStyleID(self):
        """
        Give IDs to the radio-buttons which select the marking style.

        Notes:
            Hides "mark total" style by default
            Mark style ID's are as follows
                1 = mark total = user clicks the total-mark, will likely be
                    removed in the future.
                2 = mark-up = mark starts at 0 and user increments it
                3 = mark-down = mark starts at max and user decrements it

        Returns:
            None

        """
        self.ui.markStyleGroup.setId(self.ui.markTotalRB, 1)
        self.ui.markTotalRB.hide()
        self.ui.markTotalRB.setEnabled(False)
        # continue with the other buttons
        self.ui.markStyleGroup.setId(self.ui.markUpRB, 2)
        self.ui.markStyleGroup.setId(self.ui.markDownRB, 3)

    def resizeEvent(self, event):
        """
        Resizes the image and surrounding table.

        Notes:
            Overrides QWidget.resizeEvent()
            a resize can be triggered before "getToWork" is called.

        Args:
            event (QEvent): the event to be resized.

        Returns:
            None

        """
        if hasattr(self, "testImg"):
            self.testImg.resetB.animateClick()
        if hasattr(self, "ui.tableView"):
            self.ui.tableView.resizeRowsToContents()
        super().resizeEvent(event)

    def throwSeriousError(self, error, rethrow=True):
        """
        Logs an exception, pops up a dialog and shuts down.

        Args:
            error: the exception to be reraised
            rethrow: True if the only way to solve this error is to crash
                and shut down Plom. False if the exception can be handled in a
                way other than crashing, in which case it will initiate
                shutdown and not re-raise the exception (thus avoiding a crash)

        Returns:
            None

        """
        # automatically prints a stacktrace into the log!
        log.exception("A serious error has been detected")
        msg = 'A serious error has been thrown:\n"{}"'.format(error)
        if rethrow:
            msg += "\nProbably we will crash now..."
        else:
            msg += "\nShutting down Marker."
        ErrorMessage(msg).exec_()
        self.shutDownError()
        if rethrow:
            raise (error)

    def loadMarkedList(self):
        """
        Loads the list of previously marked papers into self.examModel

        Returns:
            None

        """
        # Ask server for list of previously marked papers
        markedList = self.msgr.MrequestDoneTasks(self.question, self.version)
        for x in markedList:
            # TODO: might not the "markedList" have some other statuses?
            self.examModel.addPaper(
                ExamQuestion(
                    x[0],
                    src_img_data=[],
                    stat="marked",
                    mrk=x[1],
                    mtime=x[2],
                    tags=x[3],
                    integrity_check=x[4],
                )
            )

    def get_files_for_previously_annotated(self, task):
        """
        Loads the annotated image, the plom file, and the original source images.

        Args:
            task (str): the task for the image files to be loaded from.
                Takes the form "q1234g9" = test 1234 question 9

        Returns:
            True/False

        Raises:
            Uses error dialogs; not currently expected to throw exceptions
        """
        if len(self.examModel.getOriginalFiles(task)) > 0:
            return True

        # TODO: plom file is lovely json: why we pack it around as binary bytes?
        try:
            [page_metadata, anImage, plomfile_data] = self.msgr.MrequestImages(
                task, self.examModel.getIntegrityCheck(task)
            )
        except (PlomTaskChangedError, PlomTaskDeletedError) as ex:
            # TODO: better action we can take here?
            ErrorMessage(
                '<p>The task "{}" has changed in some way by the manager; it '
                "may need to be remarked.</p>\n\n"
                '<p>Specifically, the server says: "{}"</p>\n\n'
                "<p>This is a rare situation; just in case, we'll now force a "
                "shutdown of your client.  Sorry.</p>".format(task, str(ex))
            ).exec_()
            # This would avoid seeing the crash dialog...
            # import sys
            # sys.exit(58)
            raise PlomSeriousException("Manager changed task") from ex
        except PlomSeriousException as e:
            self.throwSeriousError(e)
            return False

        paperDir = tempfile.mkdtemp(prefix=task + "_", dir=self.workingDirectory)
        log.debug("create paperDir {} for already-graded download".format(paperDir))

        # TODO: keep more image_id, md5, server_path_filename
        src_img_data = [{"md5": x[1]} for x in page_metadata]

        # Image names = "<task>.<imagenumber>.<extension>"
        for i, row in enumerate(page_metadata):
            tmp = os.path.join(self.workingDirectory, "{}.{}.image".format(task, i))
            src_img_data[i]["filename"] = tmp
            im_bytes = self.msgr.MrequestOneImage(task, row[0], row[1])
            with open(tmp, "wb+") as fh:
                fh.write(im_bytes)
        # Parse PlomFile early for orientation data: but PageScene is going
        # to parse it later.  TODO: seems like duplication of effort.
        plomdata = json.loads(io.BytesIO(plomfile_data).getvalue())
        ori = plomdata.get("orientations")
        if not ori:
            log.warning("plom file has no orientation data: substituting zeros")
            # TODO: hardcoding orientation Issue #1306: take from server data instead in this case
            for d in src_img_data:
                d["orientation"] = 0
        else:
            log.info("importing orientations from plom file")
            for i, d in enumerate(src_img_data):
                d["orientation"] = ori[i]
        self.examModel.setOriginalFilesAndData(task, src_img_data)

        if anImage is None:
            return True

        self.examModel.setPaperDirByTask(task, paperDir)
        aname = os.path.join(paperDir, "G{}.png".format(task[1:]))
        pname = os.path.join(paperDir, "G{}.plom".format(task[1:]))
        with open(aname, "wb+") as fh:
            fh.write(anImage)
        with open(pname, "wb+") as fh:
            fh.write(plomfile_data)
        self.examModel.setAnnotatedFile(task, aname, pname)
        return True

    def _updateImage(self, pr=0):
        """
        Updates the image if needed.

        Args:
            pr (int): which row is highlighted.

        Returns:
            None
        """
        if not self.get_files_for_previously_annotated(self.prxM.getPrefix(pr)):
            return

        if self.prxM.getStatus(pr) in ("marked", "uploading...", "???"):
            self.testImg.updateImage(self.prxM.getAnnotatedFile(pr))
        else:
            # Colin doesn't understand this proxy: just pull task and query examModel
            task = self.prxM.getPrefix(pr)
            self.testImg.updateImage(self.examModel.getOriginalFiles(task))
        self.testImg.forceRedrawOrSomeBullshit()
        self.ui.tableView.setFocus()

    def updateProgress(self, val=None, maxm=None):
        """
        Updates the progress bar.

        Args:
            val (int): value for the progress bar
            maxm (int): maximum for the progress bar.

        Returns:
            None

        """

        if not val and not maxm:
            # ask server for progress update
            try:
                val, maxm = self.msgr.MprogressCount(self.question, self.version)
            except PlomSeriousException as err:
                log.exception("Serious error detected while updating progress")
                msg = 'A serious error happened while updating progress:\n"{}"'.format(
                    err
                )
                msg += "\nThis is not good: restart, report bug, etc."
                ErrorMessage(msg).exec_()
                return
        if maxm == 0:
            val, maxm = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.mProgressBar.setFormat("No papers to mark")
            ErrorMessage("No papers to mark.").exec_()
        else:
            # Neither is quite right, instead, we cache on init
            self.ui.mProgressBar.setFormat(self.ui._cachedProgressFormatStr)
        self.ui.mProgressBar.setMaximum(maxm)
        self.ui.mProgressBar.setValue(val)

    def requestNext(self):
        """
        Ask server for unmarked paper, get file, add to list, update view.

        Retry a few times in case two clients are asking for same.
        Notes:
            Side effects: on success, updates the table of tasks
            TODO: return value on success?  Currently None.
            TODO: rationalize return values

        Returns:
            None

        Raises:
            error if getting task from messenger throws PlomSeriousException

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
                task = self.msgr.MaskNextTask(self.question, self.version)
                if not task:
                    return False
            except PlomSeriousException as err:
                self.throwSeriousError(err)

            try:
                page_metadata, tags, integrity_check = self.msgr.MclaimThisTask(task)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue

        # TODO: hardcoding orientation to 0, Issue #1306
        src_img_data = [{"md5": x[1], "orientation": 0} for x in page_metadata]
        # Image names = "<task>.<imagenumber>.<extension>"
        for i, row in enumerate(page_metadata):
            # try-except? how does this fail?
            im_bytes = self.msgr.MrequestOneImage(task, row[0], row[1])
            tmp = os.path.join(self.workingDirectory, "{}.{}.image".format(task, i))
            src_img_data[i]["filename"] = tmp
            with open(tmp, "wb+") as fh:
                fh.write(im_bytes)

        self.examModel.addPaper(
            ExamQuestion(
                task,
                src_img_data=src_img_data,
                tags=tags,
                integrity_check=integrity_check,
            )
        )
        pr = self.prxM.rowFromTask(task)
        if pr is not None:
            # if newly-added row is visible, select it and redraw
            self.ui.tableView.selectRow(pr)
            self._updateImage(pr)
            # Clean up the table
            self.ui.tableView.resizeColumnsToContents()
            self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundStart(self):
        """
        Requests the next TGV in the background.

        Returns:
            None

        """
        if self.backgroundDownloader:
            log.info(
                "Previous Downloader ({}) still here, waiting".format(
                    str(self.backgroundDownloader)
                )
            )
            # if prev downloader still going than wait.  might block the gui
            self.backgroundDownloader.wait()
        # New downloader but reuse the existing Messenger clone
        self.backgroundDownloader = BackgroundDownloader(
            self.question, self.version, self._bgdownloader_msgr
        )
        self.backgroundDownloader.downloadSuccess.connect(
            self._requestNextInBackgroundFinished
        )
        self.backgroundDownloader.downloadNoneAvailable.connect(
            self.requestNextInBackgroundNoneAvailable
        )
        self.backgroundDownloader.downloadFail.connect(
            self.requestNextInBackgroundFailed
        )
        self.backgroundDownloader.start()

    def _requestNextInBackgroundFinished(
        self, task, src_img_data, tags, integrity_check
    ):
        """
        Adds paper to exam model once it's been requested.

        Args:
            task (str): the task name for the next test.
            src_img_data (list[dict]): the md5sums, filenames, etc for
                the underlying images.
            tags (str): tags for the TGV.
            integrity_check (str): integrity check string for the underlying images (concat of their md5sums)

        Returns:
            None

        """
        self.examModel.addPaper(
            ExamQuestion(
                task,
                src_img_data=src_img_data,
                tags=tags,
                integrity_check=integrity_check,
            )
        )
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()

    def requestNextInBackgroundNoneAvailable(self):
        """
        Empty.

        Notes:
            Keep this function here just in case we want to do something in the
            future.
        """
        pass

    def requestNextInBackgroundFailed(self, errmsg):
        """
        Sends an error message when requesting the next exam fails.

        Args:
            errmsg (str): Error message received.

        Returns:
            None

        """
        # TODO what should we do?  Is there a realistic way forward
        # or should we just die with an exception?
        ErrorMessage(
            "Unfortunately, there was an unexpected error downloading "
            "next paper.\n\n{}\n\n"
            "Please consider filing an issue?  I don't know if its "
            "safe to continue from here...".format(errmsg)
        ).exec_()

    def moveToNextUnmarkedTest(self, task=None):
        """
        Move the list to the next unmarked test, if possible.

        Args:
            task (str): the task number of the next unmarked test.

        Returns:
             True if move was successful, False if not, for any reason.
        """
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
        if prt == 0:  # no tasks
            return False

        prstart = None
        if task:
            prstart = self.prxM.rowFromTask(task)
        if not prstart:
            # it might be hidden by filters
            prstart = 0  # put 'start' at row=0
        pr = prstart
        while self.prxM.getStatus(pr) in ["marked", "uploading...", "deferred", "???"]:
            pr = (pr + 1) % prt
            if pr == prstart:  # don't get stuck in a loop
                break
        if pr == prstart:
            return False  # have looped over all rows and not found anything.
        self.ui.tableView.selectRow(pr)
        return True

    def deferTest(self):
        """Mark test as "defer" - to be skipped until later."""
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        if self.examModel.getStatusByTask(task) == "deferred":
            return
        if self.examModel.getStatusByTask(task) in ("marked", "uploading...", "???"):
            msg = ErrorMessage(
                "Cannot defer a marked test. We will change this in a future version."
            )
            msg.exec_()
            return
        self.examModel.deferPaper(task)

    def startTheAnnotator(self, initialData):
        """
        This fires up the annotation window for user annotation + marking.

        Args:
            initialData (list): containing things documented elsewhere
                in :func:`plom.client.annotator.Annotator.__init__`.

        Returns:
            None

        """
        mouseHand = 1 if self.ui.leftMouseCB.isChecked() else 0

        annotator = Annotator(
            self.ui.userLabel.text(),
            mouseHand,
            parentMarkerUI=self,
            initialData=initialData,
        )
        # run the annotator
        annotator.annotator_upload.connect(self.callbackAnnWantsUsToUpload)
        annotator.annotator_done_closing.connect(self.callbackAnnDoneClosing)
        annotator.annotator_done_reject.connect(self.callbackAnnDoneCancel)
        self.setEnabled(False)
        annotator.show()

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
        inidata = self.getDataForAnnotator(task)
        # make sure getDataForAnnotator did not fail
        if inidata is None:
            return

        if self.allowBackgroundOps:
            if self.examModel.countReadyToMark() == 0:
                self.requestNextInBackgroundStart()

        self.startTheAnnotator(inidata)
        # we started the annotator, we'll get a signal back when its done

    def getDataForAnnotator(self, task):
        """
        Start annotator on a particular task.

        Args:
            task (str): the task id.  If original qXXXXgYY, then annotated
                version is GXXXXgYY (G=graded).
        Returns
            data (list): (as described by startTheAnnotator) if successful.
        """
        # Create annotated filename.
        assert task.startswith("q")
        Gtask = "G" + task[1:]
        paperdir = tempfile.mkdtemp(prefix=task[1:] + "_", dir=self.workingDirectory)
        log.debug("create paperdir {} for annotating".format(paperdir))
        aname = os.path.join(paperdir, Gtask + ".png")
        cname = os.path.join(paperdir, Gtask + ".json")
        pname = os.path.join(paperdir, Gtask + ".plom")

        remarkFlag = False

        if self.examModel.getStatusByTask(task) in ("marked", "uploading...", "???"):
            msg = SimpleMessage("Continue marking paper?")
            if not msg.exec_() == QMessageBox.Yes:
                return
            remarkFlag = True
            oldpaperdir = self.examModel.getPaperDirByTask(task)
            log.debug("oldpaperdir is " + oldpaperdir)
            assert oldpaperdir is not None
            oldaname = os.path.join(oldpaperdir, Gtask + ".png")
            oldpname = os.path.join(oldpaperdir, Gtask + ".plom")
            # TODO: comment json file not downloaded
            # https://gitlab.com/plom/plom/issues/415
            shutil.copyfile(oldaname, aname)
            shutil.copyfile(oldpname, pname)

        # Yes do this even for a regrade!  We will recreate the annotations
        # (using the plom file) on top of the original file.
        fnames = self.examModel.getOriginalFiles(task)
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
        prevState = self.examModel.getStatusByTask(task)
        self.examModel.setStatusByTask(task, "ann:" + prevState)

        if remarkFlag:
            with open(pname, "r") as fh:
                pdict = json.load(fh)
        else:
            pdict = None

        exam_name = self.exam_spec["name"]
        markStyle = self.ui.markStyleGroup.checkedId()
        tgv = task[1:]
        integrity_check = self.examModel.getIntegrityCheck(task)
        src_img_data = self.examModel.get_source_image_data(task)
        return (
            tgv,
            exam_name,
            paperdir,
            aname,
            self.maxMark,
            markStyle,
            pdict,
            integrity_check,
            src_img_data,
        )

    # when Annotator done, we come back to one of these callbackAnnDone* fcns
    @pyqtSlot(str)
    def callbackAnnDoneCancel(self, task):
        """
        Called when anotator is done grading.

        Args:
            task (str): task name

        Returns:
            None

        """
        self.setEnabled(True)
        if task:
            prevState = self.examModel.getStatusByTask("q" + task).split(":")[-1]
            # TODO: could also erase the paperdir
            self.examModel.setStatusByTask("q" + task, prevState)
        # TODO: see below re "done grading".
        self._updateImage()

    @pyqtSlot(str)
    def callbackAnnDoneClosing(self, task):
        """
        Called when annotator is done grading and is closing.

        Args:
            task (str): the task ID of the current test.

        Returns:
            None

        """
        self.setEnabled(True)
        # update image view, if the row we just finished is selected
        prIndex = self.ui.tableView.selectedIndexes()
        if len(prIndex) == 0:
            return
        pr = prIndex[0].row()
        # TODO: when done grading, if ann stays open, then close, this doesn't happen
        if task:
            if self.prxM.getPrefix(pr) == "q" + task:
                self._updateImage(pr)

    @pyqtSlot(str, list)
    def callbackAnnWantsUsToUpload(self, task, stuff):
        """
        Called when annotator wants to upload.

        Args:
            task (str): the task ID of the current test.
            stuff (list): a list containing
                grade(int): grade given by marker.
                markingTime(int): total time spent marking.
                paperDir(dir): Working directory for the current task
                aname(str): annotated file name
                plomFileName(str): the name of thee .plom file
                commentFileName(str): the name of the comment file.
                integrity_check(str): the integrity_check string of the task.
                src_img_data (list[dict]): image data, md5sums, etc

        Returns:
            None

        """
        (
            gr,
            markingTime,
            paperDir,
            aname,
            plomFileName,
            commentFileName,
            integrity_check,
            src_img_data,
        ) = stuff

        if not (0 <= gr and gr <= self.maxMark):
            msg = ErrorMessage(
                "Mark of {} is outside allowed range. Rejecting. This should not happen. Please file a bug".format(
                    gr
                )
            )
            msg.exec_()
            # TODO: what do do here?  revert?
            return

        stat = self.examModel.getStatusByTask("q" + task)

        # Copy the mark, annotated filename and the markingtime into the table
        # TODO: sort this out whether task is "q00..." or "00..."?!
        self.examModel.markPaperByTask(
            "q" + task, gr, aname, plomFileName, markingTime, paperDir
        )
        # update the markingTime to be the total marking time
        totmtime = self.examModel.getMTimeByTask("q" + task)
        tags = self.examModel.getTagsByTask("q" + task)
        # TODO: should examModel have src_img_data and fnames updated too?

        _data = (
            "q" + task,  # current task
            gr,  # grade
            (
                aname,
                plomFileName,
                commentFileName,
            ),  # annotated, plom, and comment filenames
            totmtime,  # total marking time (seconds)
            self.question,
            self.version,
            tags,
            integrity_check,
            [x["md5"] for x in src_img_data],
        )
        if self.allowBackgroundOps:
            # the actual upload will happen in another thread
            self.backgroundUploader.enqueueNewUpload(*_data)
        else:
            upload(
                self.msgr,
                *_data,
                knownFailCallback=self.backgroundUploadFailedServerChanged,
                unknownFailCallback=self.backgroundUploadFailed,
                successCallback=self.backgroundUploadFinished,
            )

    def getMorePapers(self, oldtgvID):
        """
        Loads more tests.

        Args:
            oldtgvID(str): the Test-Group-Version ID for the previous test.

        Returns:
            initialData: as described by getDataForAnnotator

        """
        log.debug("Annotator wants more (w/o closing)")
        if not self.allowBackgroundOps:
            self.requestNext()
        if not self.moveToNextUnmarkedTest("q" + oldtgvID if oldtgvID else None):
            return False
        # TODO: copy paste of annotateTest()
        # probably don't need len check
        if len(self.ui.tableView.selectedIndexes()):
            row = self.ui.tableView.selectedIndexes()[0].row()
        else:
            # TODO: what to do here?
            return False
        tgvID = self.prxM.getPrefix(row)

        data = self.getDataForAnnotator(tgvID)
        # make sure getDataForAnnotator did not fail
        if data is None:
            return

        assert tgvID[1:] == data[0]
        pdict = data[-3]  # the plomdict is third-last object in data
        assert pdict is None, "Annotator should not pull a regrade"

        if self.allowBackgroundOps:
            # while annotator is firing up request next paper in background
            # after giving system a moment to do `annotator.exec_()`
            if self.examModel.countReadyToMark() == 0:
                self.requestNextInBackgroundStart()

        return data

    def PermuteAndGetSamePaper(self, task, imageList):
        """
        Allows user to reorganize pages of an exam.

        Args:
            task (str): the task ID of the current test.
            imageList (list[str]): list of image names to which are being
                rearranged.  Each row looks like `[md5, filename, angle]`.

        Returns:
            initialData (as described by getDataForAnnotator)

        """
        log.info("Rearranging image list for task {} = {}".format(task, imageList))
        # we know the list of image-refs and files. copy files into place
        # Image names = "<task>.<imagenumber>.<extension>"
        img_src_data = []
        # TODO: This code was trying (badly) to overwrite the q0001 files...
        # TODO: something with tempfile instead
        # TODO: but why not keep using old name once they are static
        rand6hex = secrets.token_hex(3)
        for i in range(len(imageList)):
            tmp = os.path.join(
                self.workingDirectory, "twist_{}_{}.{}.image".format(rand6hex, task, i)
            )
            shutil.copyfile(imageList[i][1], tmp)
            img_src_data.append(
                {
                    "md5": imageList[i][0],
                    "filename": tmp,
                    "orientation": imageList[i][2],
                }
            )
        task = "q" + task
        self.examModel.setOriginalFilesAndData(task, img_src_data)
        # set the status back to untouched so that any old plom files ignored
        self.examModel.setStatusByTask(task, "untouched")
        # finally relaunch the annotator
        return self.getDataForAnnotator(task)

    def backgroundUploadFinished(self, task, numDone, numtotal):
        """
        An upload has finished, do appropriate UI updates

        Args:
            task (str): the task ID of the current test.
            numDone (int): number of exams marked
            numTotal (int): total number of exams to mark.

        Returns:
            None

        """
        stat = self.examModel.getStatusByTask(task)
        # maybe it changed while we waited for the upload
        if stat == "uploading...":
            self.examModel.setStatusByTask(task, "marked")
        self.updateProgress(numDone, numtotal)

    def backgroundUploadFailedServerChanged(self, task, error_message):
        """An upload has failed because server changed something, safest to quit.

        Args:
            task (str): the task ID of the current test.
            error_message (str): a brief description of the error.

        Returns:
            None
        """
        self.examModel.setStatusByTask(task, "???")
        ErrorMessage(
            '<p>Background upload of "{}" has failed because the server '
            "changed something underneath us.</p>\n\n"
            '<p>Specifically, the server says: "{}"</p>\n\n'
            "<p>This is a rare situation; no data corruption has occured but "
            "your annotations have been discarded just in case.  You will be "
            "asked to redo the task later.</p>\n\n"
            "<p>For now you've been logged out and we'll now force a shutdown "
            "of your client.  Sorry.</p>".format(task, error_message)
        ).exec_()
        # This would avoid seeing the crash dialog...
        # import sys
        # sys.exit(57)
        raise PlomSeriousException(
            "Server changed under us: {}".format(error_message)
        ) from None

    def backgroundUploadFailed(self, task, errmsg):
        """An upload has failed, we don't know why, do something LOADLY.

        Args:
            task (str): the task ID of the current test.
            errmsg (str): the error message.

        Returns:
            None

        """
        self.examModel.setStatusByTask(task, "???")
        ErrorMessage(
            "Unfortunately, there was an unexpected error; the server did "
            "not accept our marked paper {}.\n\n{}\n\n"
            "If the problem persists consider filing an issue."
            "Please close this window and log in again.".format(task, errmsg)
        ).exec_()
        return

    def updateImg(self, newImg, oldImg):
        """
        Updates the displayed image when the selection has changed.

        Args:
            newImg (QItem): new image
            oldImg (QItem): old image

        Returns:
            None

        """
        idx = newImg.indexes()
        if len(idx) > 0:
            self._updateImage(idx[0].row())

    def closeEvent(self, event):
        log.debug("Something has triggered a shutdown even")
        self.do_shutdown_tasks()
        event.accept()

    def shutDownError(self):
        """Shuts down self due to error."""
        if (
            getattr(self, "_annotator", None) is not None
        ):  # try to shut down annotator too.
            self._annotator.close()
        log.error("shutting down")
        self.my_shutdown_signal.emit(2, [])
        self.close()

    def do_shutdown_tasks(self):
        """Shuts down self."""
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
            self.msgr.closeUser()
        except PlomSeriousException as err:
            self.throwSeriousError(err)

        markStyle = self.ui.markStyleGroup.checkedId()
        mouseHand = 1 if self.ui.leftMouseCB.isChecked() else 0
        sidebarRight = self.ui.sidebarRightCB.isChecked()
        self.my_shutdown_signal.emit(2, [markStyle, mouseHand, sidebarRight])

    def DNF(self):
        """
        Marks files that are not finished as "did not finish."

        Notes:
            do this for everything, not just the proxy-model

        Returns:
            None

        Raises:
            PlomSeriousException if an error occurs in server.

        """
        for r in range(self.examModel.rowCount()):
            if self.examModel.data(self.examModel.index(r, 1)) != "marked":
                # Tell server the task fo any paper that is not marked.
                # server will put that back on the todo-pile.
                try:
                    self.msgr.MdidNotFinishTask(
                        self.examModel.data(self.examModel.index(r, 0))
                    )
                except PlomSeriousException as err:
                    self.throwSeriousError(err)

    def downloadWholePaper(self, testNumber):
        """

        Args:
            testNumber (int): the test number.

        Returns:
            (tuple) containing pageData and viewFiles


        """
        try:
            pageData, imagesAsBytes = self.msgr.MrequestWholePaper(
                testNumber, self.question
            )
        except PlomTakenException as err:
            log.exception("Taken exception when downloading whole paper")
            ErrorMessage("{}".format(err)).exec_()
            return ([], [])  # TODO: what to return?

        viewFiles = []
        for iab in imagesAsBytes:
            tfn = tempfile.NamedTemporaryFile(
                dir=self.workingDirectory, suffix=".image", delete=False
            ).name
            viewFiles.append(tfn)
            with open(tfn, "wb") as fh:
                fh.write(iab)

        return [pageData, viewFiles]

    def downloadWholePaperMetadata(self, testNumber):
        """Get metadata about all images used in a particular test paper.

        Args:
            testNumber (int): the test number.

        Returns:
            (tuple) containing pageData and viewFiles
        """
        pageData = self.msgr.MrequestWholePaperMetadata(testNumber, self.question)
        return pageData

    def downloadOneImage(self, task, image_id, md5):
        """Download one image from server by its database id."""
        return self.msgr.MrequestOneImage(task, image_id, md5)

    def doneWithWholePaperFiles(self, viewFiles):
        """ Unlinks files in viewFiles to os. """
        for f in viewFiles:
            if os.path.isfile(f):
                os.unlink(f)

    def cacheLatexComments(self):
        """Caches Latexed comments."""
        clist = commentLoadAll()
        # sort list in order of longest comment to shortest comment
        clist.sort(key=lambda C: -len(C["text"]))

        # Build a progress dialog to warn user
        pd = QProgressDialog("Caching latex comments", None, 0, 2 * len(clist), self)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)
        # Start caching.
        c = 0
        pd.setValue(c)
        n = int(self.question)
        exam_name = self.exam_spec["name"]

        for X in clist:
            if commentIsVisible(X, n, exam_name) and X["text"][:4].upper() == "TEX:":
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
                pd.setLabelText("Caching:\nno tex")
                pd.setValue(c)
        pd.close()

    def latexAFragment(self, txt):
        """
        Run LaTeX on a fragment of text and return the file name of a png.

        The files are cached for reuse if the same text is passed again.

        Args:
            txt (str): the text to be Latexed.

        Returns:
            (png): a file containing the Latexed text.

        """
        if txt in self.commentCache:
            # have already latex'd this comment
            return self.commentCache[txt]
        log.debug('requesting latex for "{}"'.format(txt))
        try:
            fragment = self.msgr.MlatexFragment(txt)
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
        """ Adds a tag to the current Test."""
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        tagSet = self.examModel.getAllTags()
        currentTag = self.examModel.getTagsByTask(task)

        atb = AddTagBox(self, currentTag, list(tagSet))
        if atb.exec_() == QDialog.Accepted:
            txt = atb.TE.toPlainText().strip()
            # truncate at 256 characters.  TODO: without warning?
            if len(txt) > 256:
                txt = txt[:256]

            self.examModel.setTagsByTask(task, txt)
            # resize view too
            self.ui.tableView.resizeRowsToContents()

            # send updated tag back to server.
            try:
                self.msgr.MsetTag(task, txt)
            except PlomTakenException as err:
                log.exception("exception when trying to set tag")
                ErrorMessage('Could not set tag:\n"{}"'.format(err)).exec_()
            except PlomSeriousException as err:
                self.throwSeriousError(err)
        return

    def setFilter(self):
        """ Sets a filter tag. """
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        # check to see if invert-filter is checked
        if self.ui.filterInvCB.checkState() == Qt.Checked:
            self.prxM.filterTags(invert=True)
        else:
            self.prxM.filterTags()

    def viewSpecificImage(self):
        """ shows the image.  """
        if self.canViewAll:
            tgs = SelectTestQuestion(self.exam_spec, self.question)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = tgs.gsb.value()
            else:
                return
        else:
            tgs = SelectTestQuestion(self.exam_spec)
            if tgs.exec_() == QDialog.Accepted:
                tn = tgs.tsb.value()
                gn = self.question
            else:
                return
        task = "q{}g{}".format(str(tn).zfill(4), int(self.question))
        try:
            imageList = self.msgr.MrequestOriginalImages(task)
        except PlomNoMoreException:
            msg = ErrorMessage("No image corresponding to task {}".format(task))
            msg.exec_()
            return
        ifilenames = []
        for img in imageList:
            ifile = tempfile.NamedTemporaryFile(
                dir=self.workingDirectory, suffix=".image", delete=False
            )
            ifile.write(img)
            ifilenames.append(ifile.name)
        tvw = GroupView(ifilenames)
        tvw.setWindowTitle(
            "Original ungraded image for question {} of test {}".format(gn, tn)
        )
        tvw.exec_()
