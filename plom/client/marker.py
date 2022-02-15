# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

"""
The Plom Marker client
"""

__copyright__ = "Copyright (C) 2018-2022 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Elvis Cai", "Colin Macdonald", "Victoria Schuster"]
__license__ = "AGPL-3.0-or-later"


from collections import defaultdict
import imghdr
import json
import logging
from math import ceil
import os
from pathlib import Path
import queue
import shutil
import tempfile
from textwrap import shorten
import time
import threading

# in order to get shortcuts under OSX this needs to set this.... but only osx.
import platform

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
    QInputDialog,
    QMessageBox,
    QMenu,
    QProgressDialog,
    QWidget,
)

from plom import get_question_label
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomBadTagError,
    PlomRangeException,
    PlomVersionMismatchException,
    PlomSeriousException,
    PlomTakenException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
    PlomConflict,
    PlomException,
    PlomNoMoreException,
    PlomNoSolutionException,
)
from plom.messenger import Messenger
from .annotator import Annotator
from .image_view_widget import ImageViewWidget
from .origscanviewer import QuestionViewDialog, SelectTestQuestion
from .uiFiles.ui_marker import Ui_MarkerWindow
from .useful_classes import AddRemoveTagDialog
from .useful_classes import ErrorMessage, SimpleQuestion

if platform.system() == "Darwin":
    from PyQt5.QtGui import qt_set_sequence_auto_mnemonic

    qt_set_sequence_auto_mnemonic(True)

log = logging.getLogger("marker")


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

    downloadSuccess = pyqtSignal(str, list, list, list, str)
    downloadNoneAvailable = pyqtSignal()
    downloadFail = pyqtSignal(str)

    def __init__(self, question, version, msgr_clone, workdir):
        """
        Initializes a new downloader.

        Args:
            question (str): question number
            version (str): version number.
            msgr_clone (Messenger): use this for the actual downloads.
                Note Messenger is not multithreaded and blocks using
                mutexes, so you may want to pass a clone of your
                Messenger, rather than the one you are using yourself!
            workdir (pathlib.Path): filespace for downloading.

        Notes:
            question/version may be able to be type int as well.
        """
        super().__init__()
        self.question = question
        self.version = version
        self.workingDirectory = workdir
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
                page_metadata, tags, integrity_check = self._msgr.MclaimThisTask(
                    task, version=self.version
                )
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
            except PlomSeriousException as err:
                self.downloadFail.emit(str(err))
                self.quit()

        num = int(task[1:5])
        full_pagedata = self._msgr.MrequestWholePaperMetadata(num, self.question)
        for r in full_pagedata:
            r["local_filename"] = None
        # don't save in _full_pagedata b/c we're in another thread: see downloadSuccess emitted below

        src_img_data = [{"id": x[0], "md5": x[1]} for x in page_metadata]
        del page_metadata

        # Populate the orientation keys from the full pagedata
        for i, row in enumerate(src_img_data):
            ori = [r["orientation"] for r in full_pagedata if r["id"] == row["id"]]
            # There could easily be more than one: what if orientation is contradictory?
            row["orientation"] = ori[0]  # just take first one

        # Image names = "<task>.<imagenumber>.<extension>"
        # TODO: use server filename from server_path_filename
        for i, row in enumerate(src_img_data):
            # TODO: add a "aggressive download" option to get all.
            # try-except? how does this fail?
            im_bytes = self._msgr.MrequestOneImage(row["id"], row["md5"])
            im_ext = imghdr.what(None, h=im_bytes)
            tmp = self.workingDirectory / "{}.{}.{}".format(task, i, im_ext)
            with open(tmp, "wb") as fh:
                fh.write(im_bytes)
            row["filename"] = str(tmp)
            for r in full_pagedata:
                if r["md5"] == row["md5"]:
                    r["local_filename"] = tmp

        self.downloadSuccess.emit(
            task, src_img_data, full_pagedata, tags, integrity_check
        )
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
        self.q = None
        self.is_upload_in_progress = False
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
        log.debug("upQ enqueuing item from main thread " + str(threading.get_ident()))
        self.q.put(args)

    def queue_size(self):
        """Return the number of papers waiting or currently uploading."""
        if self.is_upload_in_progress:
            return self.q.qsize() + 1
        return self.q.qsize()

    def isEmpty(self):
        """
        Checks if the upload queue is empty.

        Returns:
            True if the upload queue is empty, false otherwise.
        """
        # return self.q.empty()
        return self.queue_size() == 0

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
            self.is_upload_in_progress = True
            # TODO: remove so that queue needs no knowledge of args
            code = data[0]
            log.info("upQ thread: popped code {} from queue, uploading".format(code))
            # For experimenting with slow uploads
            # time.sleep(30)
            upload(
                self._msgr,
                *data,
                knownFailCallback=self.uploadKnownFail.emit,
                unknownFailCallback=self.uploadUnknownFail.emit,
                successCallback=self.uploadSuccess.emit,
            )
            self.is_upload_in_progress = False

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
    rubrics,
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
        PlomSeriousException: elements in filenames do not correspond to
            the same exam.
    """
    # do name sanity checks here
    aname, pname = filenames

    if not (
        task.startswith("q")
        and aname.stem == f"G{task[1:]}"
        and pname.name == f"G{task[1:]}.plom"
    ):
        raise PlomSeriousException(
            "Upload file names mismatch [{}, {}] - this should not happen".format(
                aname, pname
            )
        )
    try:
        msg = _msgr.MreturnMarkedTask(
            task,
            question,
            ver,
            grade,
            mtime,
            aname,
            pname,
            rubrics,
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
    number, group, version, status, the mark, the original image
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
        tags=[],
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
            tags (list): Tags corresponding to the exam.  We will flatten to
                a space-separaed string.
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
        # The filename for the (future) annotated image
        self.annotatedFile = ""
        self.plomFile = ""  # The filename for the (future) plom file
        self.markingTime = mtime
        self.tags = " ".join(tags)
        self.integrity_check = integrity_check


class MarkerExamModel(QStandardItemModel):
    """A tablemodel for handling the group image marking data."""

    def __init__(self, parent=None):
        """
        Initializes a new MarkerExamModel.

        Args:
            parent (QStandardItemModel): MarkerExamModel's Parent.

        """
        super().__init__(parent)
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
            int: the row identifier of the added paper.

        """
        # check if paper is already in model - if so, delete it and add it back with the new data.
        # **but** be careful - if annotation in progress then ??
        try:
            r = self._findTask(paper.prefix)
        except ValueError:
            pass
        else:
            ErrorMessage(
                f"Task {paper.prefix} has been modified by server - you will need to annotate it again."
            ).exec_()
            self.removeRow(r)
        # Append new groupimage to list and append new row to table.
        r = self.rowCount()
        # hide -1 which upstream tooling uses "not yet marked"
        try:
            markstr = str(paper.mark) if int(paper.mark) >= 0 else ""
        except ValueError:
            markstr = ""
        # TODO: these *must* be strings but I don't understand why
        self.appendRow(
            [
                QStandardItem(paper.prefix),
                QStandardItem(paper.status),
                QStandardItem(markstr),
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
            str: the prefix of the image

        """
        return self.data(self.index(r, 0))

    def _getStatus(self, r):
        """
        Returns the status of the image.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            str: the status of the image

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
            dir: a temporary directory for this paper.
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
        """Return a list of tags for task.

        TODO: can we draw flat, but use list for storing?
        """
        return self._getDataByTask(task, 4).split()

    def setTagsByTask(self, task, tags):
        """Set a list of tags for task.
        Note: internally stored as flattened string.
        """
        return self._setDataByTask(task, 4, " ".join(tags))

    def getMTimeByTask(self, task):
        """Return total marking time (s) for task, (task(str), return (int).)"""
        return int(self._getDataByTask(task, 3))

    def getAnnotatedFileByTask(self, task):
        """Returns the filename of the annotated image."""
        return Path(self._getDataByTask(task, 6))

    def getPlomFileByTask(self, task):
        """Returns the filename of the plom json data."""
        return Path(self._getDataByTask(task, 7))

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
        self.setData(self.index(r, 3), str(mtime + mt))
        self._setStatus(r, "uploading...")
        self.setData(self.index(r, 2), str(mrk))
        self._setAnnotatedFile(r, aname, pname)
        self._setPaperDir(r, tdir)

    def deferPaper(self, task):
        """Sets the status for the task's paper to deferred."""
        self.setStatusByTask(task, "deferred")

    def removePaper(self, task):
        """Removes the task's paper from self."""
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
        super().__init__(parent)
        self.setFilterKeyColumn(4)
        self.filterString = ""
        self.invert = False

    def lessThan(self, left, right):
        """
        Sees if left data is less than right data.

        Args:
            left (QModelIndex):
            right (QModelIndex):

        Returns:
            bool: if both can be converted to int, compare as ints.
            Otherwise, convert to strings and compare.
        """
        # try to compare as integers
        try:
            return int(left.data()) < int(right.data())
        except (ValueError, TypeError):
            pass
        # else compare as strings
        return str(left.data()) < str(right.data())

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
        Checks if a row matches the current filter.

        Notes:
            Overrides base method.

        Args:
            pos (int): row being checked.
            index (any): unused.

        Returns:
            bool: True if filter accepts the row, False otherwise.

        The filter string is first broken into words.  All of those words
        must be in the tags of the row, in any order.  The `invert` flag
        inverts that logic: at least one of the words must not be in the
        tags.
        """
        search_terms = self.filterString.casefold().split()
        tags = self.sourceModel().data(self.sourceModel().index(pos, 4)).casefold()
        all_search_terms_in_tags = all(x in tags for x in search_terms)
        if self.invert:
            return not all_search_terms_in_tags
        return all_search_terms_in_tags

    def getPrefix(self, r):
        """
        Returns the task code of inputted row index.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            str: the prefix of the paper indicated by r.

        """
        return self.data(self.index(r, 0))

    def getStatus(self, r):
        """
        Returns the status of inputted row index.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            str: the status of the paper indicated by r.

        """
        # Return the status of the image
        return self.data(self.index(r, 1))

    def getAnnotatedFile(self, r):
        """
        Returns the file names of the annotated image of r.

        Args:
            r (int): the row identifier of the paper.

        Returns:
            str: the file name of the annotated image of the paper in r.

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

    def __init__(self, Qapp, tmpdir=None):
        """
        Initialize a new MarkerClient

        Args:
            Qapp(QApplication): Main client application
            tmpdir (pathlib.Path/str/None): a temporary directory for
                storing image files and other data.  In principle can
                be shared with Identifier although this may not be
                implemented.  If `None`, we will make our own.
        """
        super().__init__()
        self.Qapp = Qapp

        # Save the local temp directory for image files and the class list.
        if not tmpdir:
            tmpdir = tempfile.mkdtemp(prefix="plom_")
        self.workingDirectory = Path(tmpdir)

        self.maxMark = -1  # temp value
        # TODO: a not-fully-thought-out datastore for immutable pagedata
        # Note: specific to this question
        self._full_pagedata = {}
        self.examModel = (
            MarkerExamModel()
        )  # Exam model for the table of groupimages - connect to table
        self.prxM = ProxyModel()  # set proxy for filtering and sorting
        # A view window for the papers so user can zoom in as needed.
        self.testImg = ImageViewWidget(self)
        self.annotatorSettings = defaultdict(
            lambda: None
        )  # settings variable for annotator settings (initially None)
        self.commentCache = {}  # cache for Latex Comments
        self.backgroundDownloader = None
        self.backgroundUploader = None

        self.allowBackgroundOps = True

        # instance vars that get initialized later
        self.question = None
        self.version = None
        self.exam_spec = None
        self.ui = None
        self.msgr = None
        self._cachedProgressFormatStr = None

    def setup(self, messenger, question, version, lastTime):
        """Performs setup procedure for markerClient.

        TODO: move all this into init?

        TODO: verify all lastTime Params, there are almost certainly some missing

        Args:
            messenger (Messenger): handle communication with server.
            question (int): question number.
            version (int): version number
            lastTime (dict): settings.
                containing::

                   {
                     "POWERUSER"
                     "FOREGROUND"
                     "CommentsWarnings"
                     "MarkWarnings"
                     "SidebarOnRight"
                   }

                and potentially others

        Returns:
            None
        """
        self.msgr = messenger
        # BackgroundDownloaders come and go but share a single cloned Messenger
        # Note: BackgroundUploader is persistent and makes its own clone.
        self._bgdownloader_msgr = Messenger.clone(self.msgr)
        self.question = question
        self.version = version

        # Get the number of Tests, Pages, Questions and Versions
        # Note: if this fails UI is not yet in a usable state
        self.exam_spec = self.msgr.get_spec()

        self.UIInitialization()
        self.applyLastTimeOptions(lastTime)
        self.connectGuiButtons()

        try:
            self.maxMark = self.msgr.MgetMaxMark(self.question, self.version)
        except PlomRangeException as err:
            ErrorMessage(str(err)).exec_()
            return
        self.ui.maxscoreLabel.setText(str(self.maxMark))

        # Get list of papers already marked and add to table.
        self.loadMarkedList()

        # Keep the original format around in case we need to change it
        self._cachedProgressFormatStr = self.ui.mProgressBar.format()
        self.updateProgress()  # Update counts

        # Connect the view **after** list updated.
        # Connect the table-model's selection change to appropriate function
        self.ui.tableView.selectionModel().selectionChanged.connect(self.updateImg)

        self.requestNext()  # Get a question to mark from the server
        # reset the view so whole exam shown.
        self.testImg.resetView()
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

        if lastTime.get("FOREGROUND", False):
            self.allowBackgroundOps = False

        self.ui.sidebarRightCB.setChecked(lastTime.get("SidebarOnRight", False))

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
        try:
            question_label = get_question_label(self.exam_spec, self.question)
        except (ValueError, KeyError):
            question_label = "???"
        self.ui.infoBox.setTitle(
            "Marking {} (ver. {}) of “{}”".format(
                question_label, self.version, self.exam_spec["name"]
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
        self.ui.tableView.hideColumn(10)

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
        m = QMenu()
        m.addAction("Get nth...", self.requestInteractive)
        self.ui.getNextButton.setMenu(m)
        # self.ui.getNextButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        self.ui.deferButton.clicked.connect(self.deferTest)
        self.ui.tagButton.clicked.connect(self.manage_tags)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        self.ui.filterInvCB.stateChanged.connect(self.setFilter)
        self.ui.viewButton.clicked.connect(self.view_testnum_question)

    def resizeEvent(self, event):
        """
        Resizes the image and surrounding table.

        Notes:
            Overrides QWidget.resizeEvent()
            a resize can be triggered before "setup" is called.
            TODO: which is more evidence that "init" should consume "setup"

        Args:
            event (QEvent): the event to be resized.

        Returns:
            None

        """
        if hasattr(self, "testImg"):
            self.testImg.resetView()
        if hasattr(self, "ui.tableView"):
            self.ui.tableView.resizeRowsToContents()
        super().resizeEvent(event)

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

        assert task[0] == "q"
        assert task[5] == "g"
        num = int(task[1:5])
        question = int(task[6:])
        assert question == self.question

        try:
            integrity = self.examModel.getIntegrityCheck(task)
            plomdata = self.msgr.get_annotations(
                num, self.question, edition=None, integrity=integrity
            )
            annotated_image = self.msgr.get_annotations_image(
                num, self.question, edition=plomdata["annotation_edition"]
            )
        except (PlomTaskChangedError, PlomTaskDeletedError) as ex:
            # TODO: better action we can take here?
            # TODO: the real problem here is that the full_pagedata is potentially out of date!
            # TODO: we also need (and maybe already have) a mechanism to invalidate existing annotations
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

        # Not yet easy to use full_pagedata to build src_img_data (e.g., "included"
        # column means different things).  Instead, extract from .plom file.
        full_pagedata = self.msgr.MrequestWholePaperMetadata(num, self.question)
        for r in full_pagedata:
            r["local_filename"] = None
        self._full_pagedata[num] = full_pagedata

        log.info("importing source image data (orientations etc) from .plom file")
        # filenames likely stale
        src_img_data = plomdata["base_images"]

        # Image names = "<task>.<imagenumber>.<extension>"
        # TODO: use server filename from server_path_filename
        for i, row in enumerate(src_img_data):
            im_bytes = self.msgr.MrequestOneImage(row["id"], row["md5"])
            im_type = imghdr.what(None, h=im_bytes)
            tmp = self.workingDirectory / "{}.{}.{}".format(task, i, im_type)
            with open(tmp, "wb") as fh:
                fh.write(im_bytes)
            row["filename"] = str(tmp)
            for r in full_pagedata:
                if r["md5"] == row["md5"]:
                    r["local_filename"] = tmp

        self.examModel.setOriginalFilesAndData(task, src_img_data)

        paperdir = tempfile.mkdtemp(prefix=task + "_", dir=self.workingDirectory)
        paperdir = Path(paperdir)
        log.debug("create paperdir %s for already-graded download", paperdir)
        self.examModel.setPaperDirByTask(task, paperdir)
        im_type = imghdr.what(None, h=annotated_image)
        aname = paperdir / "G{}.{}".format(task[1:], im_type)
        pname = paperdir / "G{}.plom".format(task[1:])
        with open(aname, "wb") as fh:
            fh.write(annotated_image)
        with open(pname, "w") as f:
            json.dump(plomdata, f, indent="  ")
            f.write("\n")
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
                log.exception("Serious error detected while updating progress: %s", err)
                msg = f"A serious error happened while updating progress:\n{err}"
                msg += "\nThis is not good: restart, report bug, etc."
                ErrorMessage(msg).exec_()
                return
        if maxm == 0:
            val, maxm = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.mProgressBar.setFormat("No papers to mark")
            ErrorMessage("No papers to mark.").exec_()
        else:
            # Neither is quite right, instead, we cache on init
            self.ui.mProgressBar.setFormat(self._cachedProgressFormatStr)
        self.ui.mProgressBar.setMaximum(maxm)
        self.ui.mProgressBar.setValue(val)

    def requestInteractive(self):
        """Ask user for paper number and then ask server for that paper.

        If available, download stuff, add to list, update view.
        """
        s = "<p>Which paper number would you like to get?</p>"
        s += f"<p>Note: you are marking version {self.version} of question {self.question}.</p>"
        max_papernum = self.exam_spec["numberToProduce"]
        n, ok = QInputDialog.getInt(self, "Which paper to get", s, 1, 1, max_papernum)
        if not ok:
            return
        log.info("getting paper num %s", n)
        try:
            self.requestParticularPaper(n)
        except (
            PlomTakenException,
            PlomRangeException,
            PlomVersionMismatchException,
        ) as err:
            ErrorMessage(f"Cannot get get paper {n}: {err}").exec_()

    def requestNext(self):
        """Ask server for an unmarked paper, get file, add to list, update view.

        Retry a few times in case two clients are asking for same.

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
            try:
                task = self.msgr.MaskNextTask(self.question, self.version)
                if not task:
                    return
            except PlomSeriousException as err:
                log.exception("Unexpected error getting next task: %s", err)
                ErrorMessage(
                    f"Unexpected error getting next task:\n{err}\nClient will now crash!"
                ).exec_()
                raise

            num = int(task[1:5])
            try:
                self.requestParticularPaper(num)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue

    def requestParticularPaper(self, papernum):
        """Try to get a given paper number from the server.

        Notes:
            Side effects: on success, updates the table of tasks

        Returns:
            None

        Raises:
            PlomTakenException
            PlomVersionMismatchException
        """
        task = f"q{papernum:04}g{self.question}"
        page_metadata, tags, integrity_check = self.msgr.MclaimThisTask(
            task, version=self.version
        )
        full_pagedata = self.msgr.MrequestWholePaperMetadata(papernum, self.question)
        for r in full_pagedata:
            r["local_filename"] = None
        self._full_pagedata[papernum] = full_pagedata

        src_img_data = [{"id": x[0], "md5": x[1]} for x in page_metadata]
        del page_metadata

        # Populate the orientation keys from the full pagedata
        for i, row in enumerate(src_img_data):
            ori = [r["orientation"] for r in full_pagedata if r["id"] == row["id"]]
            # There could easily be more than one: what if orientation is contradictory?
            row["orientation"] = ori[0]  # just take first one

        # Image names = "<task>.<imagenumber>.<extension>"
        # TODO: use server filename from server_path_filename
        for i, row in enumerate(src_img_data):
            # TODO: add a "aggressive download" option to get all.
            # try-except? how does this fail?
            im_bytes = self.msgr.MrequestOneImage(row["id"], row["md5"])
            im_ext = imghdr.what(None, h=im_bytes)
            tmp = self.workingDirectory / "{}.{}.{}".format(task, i, im_ext)
            with open(tmp, "wb") as fh:
                fh.write(im_bytes)
            row["filename"] = str(tmp)
            for r in full_pagedata:
                if r["md5"] == row["md5"]:
                    r["local_filename"] = tmp

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
            self.question, self.version, self._bgdownloader_msgr, self.workingDirectory
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
        self, task, src_img_data, full_pagedata, tags, integrity_check
    ):
        """
        Adds paper to exam model once it's been requested.

        Args:
            task (str): the task name for the next test.
            src_img_data (list[dict]): the md5sums, filenames, etc for
                the underlying images.
            full_pagedata (list): temporary hacks to merge with above?
            tags (list[str]): list of texts for tags for the TGV.
            integrity_check (str): integrity check string for the underlying images (concat of their md5sums)

        Returns:
            None
        """
        num = int(task[1:5])
        self._full_pagedata[num] = full_pagedata
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
                    msg = SimpleQuestion(
                        self,
                        "Still waiting for downloader to get the next image.  "
                        "Do you want to wait a few more seconds?\n\n"
                        "(It is safe to choose 'no': the Annotator will simply close)",
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
        annotator = Annotator(
            self.ui.userLabel.text(),
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
        Returns:
            list/None: as described by startTheAnnotator, if successful.
        """
        # Create annotated filename.
        assert task.startswith("q")
        paperdir = tempfile.mkdtemp(prefix=task[1:] + "_", dir=self.workingDirectory)
        paperdir = Path(paperdir)
        log.debug("create paperdir %s for annotating", paperdir)
        Gtask = "G" + task[1:]
        # note no extension yet
        aname = paperdir / Gtask
        pdict = None

        if self.examModel.getStatusByTask(task) in ("marked", "uploading...", "???"):
            msg = SimpleQuestion(self, "Continue marking paper?")
            if not msg.exec_() == QMessageBox.Yes:
                return
            oldpname = self.examModel.getPlomFileByTask(task)
            with open(oldpname, "r") as fh:
                pdict = json.load(fh)

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
                    msg = SimpleQuestion(
                        self,
                        "Still waiting for download.  Do you want to wait a bit longer?",
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

        exam_name = self.exam_spec["name"]

        # TODO: I dislike this packed-string: overdue for refactor
        assert task[5] == "g"
        question_num = int(task[6:])
        tgv = task[1:]
        question_label = get_question_label(self.exam_spec, question_num)
        integrity_check = self.examModel.getIntegrityCheck(task)
        src_img_data = self.examModel.get_source_image_data(task)
        return (
            tgv,
            question_label,
            exam_name,
            paperdir,
            aname,
            self.maxMark,
            pdict,
            integrity_check,
            src_img_data,
        )

    def getRubricsFromServer(self, question=None):
        """Get list of rubrics from server.

        Args:
            question (int/None)

        Returns:
            list: A list of the dictionary objects.
        """
        if question is None:
            return self.msgr.MgetRubrics()
        return self.msgr.MgetRubricsByQuestion(question)

    def sendNewRubricToServer(self, new_rubric):
        return self.msgr.McreateRubric(new_rubric)

    def modifyRubricOnServer(self, key, updated_rubric):
        return self.msgr.MmodifyRubric(key, updated_rubric)

    def getSolutionImage(self):
        # get the file from disc if it exists, else grab from server
        soln = os.path.join(
            self.workingDirectory,
            "solution.{}.{}.png".format(self.question, self.version),
        )
        if os.path.isfile(soln):
            return soln
        else:
            return self.refreshSolutionImage()

    def refreshSolutionImage(self):
        # get solution and save it to temp dir
        soln = os.path.join(
            self.workingDirectory,
            "solution.{}.{}.png".format(self.question, self.version),
        )
        try:
            im_bytes = self.msgr.getSolutionImage(self.question, self.version)
            with open(soln, "wb") as fh:
                fh.write(im_bytes)
            return soln
        except PlomNoSolutionException:
            # if a residual file is there, delete it
            if os.path.isfile(soln):
                os.remove(soln)
            return None

    def saveTabStateToServer(self, tab_state):
        """Upload a tab state to the server."""
        log.info("Saving user's rubric tab configuration to server")
        self.msgr.MsaveUserRubricTabs(self.question, tab_state)

    def getTabStateFromServer(self):
        """Download the state from the server."""
        log.info("Pulling user's rubric tab configuration from server")
        return self.msgr.MgetUserRubricTabs(self.question)

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
                plomFileName(str): the name of the .plom file
                rubric(list[str]): the keys of the rubrics used
                integrity_check(str): the integrity_check string of the task.
                src_img_data (list[dict]): image data, md5sums, etc

        Returns:
            None
        """
        (
            grade,
            markingTime,
            paperDir,
            aname,
            plomFileName,
            rubrics,
            integrity_check,
            src_img_data,
        ) = stuff
        if not isinstance(grade, (int, float)):
            raise RuntimeError(f"Mark {grade} type {type(grade)} is not a number")
        if not (0 <= grade and grade <= self.maxMark):
            raise RuntimeError(
                f"Mark {grade} outside allowed range [0, {self.maxMark}]. Please file a bug!"
            )
        # TODO: sort this out whether task is "q00..." or "00..."?!
        task = "q" + task

        # TODO: this was unused?  comment out for now...
        # stat = self.examModel.getStatusByTask(task)

        # Copy the mark, annotated filename and the markingtime into the table
        self.examModel.markPaperByTask(
            task, grade, aname, plomFileName, markingTime, paperDir
        )
        # update the markingTime to be the total marking time
        totmtime = self.examModel.getMTimeByTask(task)
        # TODO: should examModel have src_img_data and fnames updated too?

        _data = (
            task,
            grade,
            (
                aname,
                plomFileName,
            ),
            totmtime,  # total marking time (seconds)
            self.question,
            self.version,
            rubrics,
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
        """User has reorganized pages of an exam.

        Args:
            task (str): the task ID of the current test.
            imageList (list[str]): list of image names to which are being
                rearranged.  Each row looks like `[md5, filename, angle]`.

        Returns:
            tuple: initialData (as described by :meth:`startTheAnnotator`.)
        """
        log.info("Rearranging image list for task {} = {}".format(task, imageList))
        # we know the list of image-refs and files. copy files into place
        # Image names = "<task>.<imagenumber>.<extension>"
        src_img_data = []
        # TODO: This code was trying (badly) to overwrite the q0001 files...
        # TODO: but why not keep using old name once they are static
        for i in range(len(imageList)):
            with tempfile.NamedTemporaryFile(
                dir=self.workingDirectory,
                prefix="twist_{}_{}_".format(task, i),
                suffix="_" + Path(imageList[i][1]).name,
                delete=False,
            ) as f:
                tmp = Path(f.name)
            shutil.copyfile(imageList[i][1], tmp)
            src_img_data.append(
                {
                    "id": imageList[i][3],
                    "md5": imageList[i][0],
                    "filename": str(tmp),
                    "orientation": imageList[i][2],
                }
            )
        task = "q" + task
        self.examModel.setOriginalFilesAndData(task, src_img_data)
        # set the status back to untouched so that any old plom files ignored
        self.examModel.setStatusByTask(task, "untouched")
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
            "<p>This is a rare situation; no data corruption has occurred but "
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
        """An upload has failed, we don't know why, do something LOUDLY.

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

    def get_upload_queue_length(self):
        """How long is the upload queue?

        An overly long queue might be a sign of network troubles.

        Returns:
            int: The number of papers waiting to upload, possibly but
            not certainly including the current upload-in-progress.
            Value might also be approximate.
        """
        if not self.backgroundUploader:
            return 0
        return self.backgroundUploader.queue_size()

    def wait_for_bguploader(self, timeout=0):
        """Wait for the uploader queue to empty.

        Args:
            timeout (int): return early after approximately `timeout`
                seconds.  If 0 then wait forever.

        Returns:
            bool: True if it shutdown.  False if we timed out.
        """
        dt = 0.1  # timestep
        if timeout != 0:
            N = ceil(float(timeout) / dt)
        else:
            N = 0  # zero/infinity: pretty much same
        M = ceil(2.0 / dt)  # warn every M seconds
        if self.backgroundUploader:
            count = 0
            while self.backgroundUploader.isRunning():
                if self.backgroundUploader.isEmpty():
                    # don't try to quit until the queue is empty
                    self.backgroundUploader.quit()
                time.sleep(dt)
                count += 1
                if N > 0 and count >= N:
                    log.warning(
                        "Timed out after {} seconds waiting for uploader to finish".format(
                            timeout
                        )
                    )
                    return False
                if count % M == 0:
                    log.warning("Still waiting for uploader to finish...")
            self.backgroundUploader.wait()
        return True

    def closeEvent(self, event):
        log.debug("Something has triggered a shutdown event")
        N = self.get_upload_queue_length()
        if N > 0:
            msg = QMessageBox()
            s = "<p>There is 1 paper" if N == 1 else f"<p>There are {N} papers"
            s += " uploading or queued for upload.</p>"
            msg.setText(s)
            s = "<p>You may want to cancel and wait a few seconds.</p>\n"
            s += "<p>If you&apos;ve already tried that, then the upload "
            s += "may have failed: you can quit, losing any non-uploaded "
            s += "annotations.</p>"
            msg.setInformativeText(s)
            msg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Discard)
            msg.setDefaultButton(QMessageBox.Cancel)
            button = msg.button(QMessageBox.Cancel)
            button.setText("Wait (cancel close)")
            msg.setIcon(QMessageBox.Warning)
            if msg.exec_() == QMessageBox.Cancel:
                event.ignore()
                return
        if self.backgroundUploader is not None:
            # politely ask one more time
            if self.backgroundUploader.isRunning():
                self.backgroundUploader.quit()
            if not self.backgroundUploader.wait(50):
                log.info("Background downloader did stop cleanly in 50ms, terminating")
            # then nuke it from orbit
            if self.backgroundUploader.isRunning():
                self.backgroundUploader.terminate()

        log.debug("Revoking login token")
        try:
            self.msgr.closeUser()
        except PlomAuthenticationException:
            log.warn("User tried to logout but was already logged out.")
            pass
        sidebarRight = self.ui.sidebarRightCB.isChecked()
        log.debug("Emitting Marker shutdown signal")
        self.my_shutdown_signal.emit(2, [sidebarRight])
        event.accept()
        log.debug("Marker: goodbye!")

    def downloadWholePaper(self, testNumber):
        """Legacy method, yet another way of getting images.

        Args:
            testNumber (int): the test number.

        Returns:
            tuple: containing pageData and viewFiles.  You are responsible
            for deleting the files when done with them, in particular
            these may include duplicate images.
        """
        try:
            pageData, imagesAsBytes = self.msgr.MrequestWholePaper(
                testNumber, self.question
            )
        except PlomTakenException as err:
            log.exception("Taken exception while downloading whole paper %s", err)
            ErrorMessage(
                f"'Taken exception' while downloading whole paper:\n{err}"
            ).exec_()
            return ([], [])

        viewFiles = []
        for iab in imagesAsBytes:
            im_type = imghdr.what(None, h=iab)
            with tempfile.NamedTemporaryFile(
                "wb", dir=self.workingDirectory, suffix=f".{im_type}", delete=False
            ) as f:
                f.write(iab)
                viewFiles.append(Path(f.name))

        return (pageData, viewFiles)

    def downloadOneImage(self, image_id, md5):
        """Download one image from server by its database id."""
        return self.msgr.MrequestOneImage(image_id, md5)

    def doneWithWholePaperFiles(self, viewFiles):
        """Unlinks files in viewFiles to os."""
        for f in viewFiles:
            if os.path.isfile(f):
                os.unlink(f)

    def cacheLatexComments(self):
        """Caches Latexed comments."""
        if True:
            log.debug("TODO: currently skipping LaTeX pre-rendering, see Issue #1491")
            return

        clist = []
        # sort list in order of longest comment to shortest comment
        clist.sort(key=lambda C: -len(C["text"]))

        # Build a progress dialog to warn user
        pd = QProgressDialog("Caching latex comments", None, 0, 3 * len(clist), self)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)
        # Start caching.
        c = 0
        pd.setValue(c)

        for X in clist:
            if X["text"][:4].upper() == "TEX:":
                txt = X["text"][4:].strip()
                pd.setLabelText("Caching:\n{}".format(txt[:64]))
                # latex the red version
                self.latexAFragment(txt, quiet=True)
                c += 1
                pd.setValue(c)
                # and latex the previews (legal and illegal versions)
                txtp = (
                    "\\color{blue}" + txt
                )  # make color blue for ghost rendering (legal)
                self.latexAFragment(txtp, quiet=True)
                c += 1
                pd.setValue(c)
                txtp = (
                    "\\color{gray}" + txt
                )  # make color gray for ghost rendering (illegal)
                self.latexAFragment(txtp, quiet=True)
                c += 1
                pd.setValue(c)
            else:
                c += 3
                pd.setLabelText("Caching:\nno tex")
                pd.setValue(c)
        pd.close()

    def latexAFragment(
        self, txt, *, quiet=False, cache_invalid=True, cache_invalid_tryagain=False
    ):
        """
        Run LaTeX on a fragment of text and return the file name of a png.

        The files are cached for reuse if the same text is passed again.

        Args:
            txt (str): the text to be Latexed.

        Keyword Args:
            quiet (bool): if True, don't popup dialogs on errors.
                Caution: this can result in a lot of API calls because
                users can keep requesting the same (bad) TeX from the
                server, e.g., by having bad TeX in a rubric.
            cache_invalid (bool): whether to cache invalid TeX.  Useful
                to prevent repeated calls to render bad TeX but might
                prevent users from seeing (again) an error dialog that
            try_again_if_cache_invalid (bool): if True then when we get
                a cache hit of `None` (corresponding to bad TeX) then we
                try to to render again.

        Returns:
            pathlib.Path/str/None: a path and filename to a ``.png`` of
            the rendered TeX.  Or None if there was an error: callers
            will need to decide how to handle that, typically by
            displaying the raw code instead.
        """
        txt = txt.strip()
        # If we already latex'd this text, return the cached image
        try:
            r = self.commentCache[txt]
        except KeyError:
            # logic is convoluted: this is cache-miss...
            r = None
        else:
            # ..and this is cache-hit of None
            if r is None and not cache_invalid_tryagain:
                log.debug(
                    "tex: cache hit None, tryagain NOT set: %s",
                    shorten(txt, 60, placeholder="..."),
                )
                return None
        if r:
            return r
        log.debug("tex: request image for: %s", shorten(txt, 80, placeholder="..."))
        r, fragment = self.msgr.MlatexFragment(txt)
        if not r:
            if not quiet:
                # Heuristics to highlight error: latex errors seem to start with "! "
                lines = fragment.split("\n")
                idx = [i for i, line in enumerate(lines) if line.startswith("! ")]
                if any(idx):
                    n = idx[0]  # could be fancier if more than one match
                    info = "\n".join(lines[max(0, n - 5) : n + 5])
                    ErrorMessage(
                        """
                        <p>The server reported an error processing your TeX fragment.</p>
                        <p>Perhaps the error is visible in the following snippet,
                        otherwise see full logs under details:</p>
                        """,
                        details=fragment,
                        info=info,
                    ).exec_()
                else:
                    ErrorMessage(
                        "<p>The server reported an error processing your TeX fragment.</p>",
                        details=fragment,
                    ).exec_()
            if cache_invalid:
                self.commentCache[txt] = None
            return None
        with tempfile.NamedTemporaryFile(
            "wb", dir=self.workingDirectory, suffix=".png", delete=False
        ) as f:
            f.write(fragment)
            fragFile = f.name
        # add it to the cache
        self.commentCache[txt] = fragFile
        return fragFile

    def manage_tags(self):
        """Manage the tags of the current task."""
        if len(self.ui.tableView.selectedIndexes()):
            pr = self.ui.tableView.selectedIndexes()[0].row()
        else:
            return
        task = self.prxM.getPrefix(pr)
        self.manage_task_tags(task)

    def manage_task_tags(self, task, parent=None):
        """Manage the tags of a task.

        args:
            task (str): A string like "q0003g2" for paper 3 question 2.

        keyword args:
            parent (Window/None): Which window should be dialog's parent?
                If None, then use `self` (which is Marker) but if other
                windows (such as Annotator or PageRearranger) are calling
                this and if so they should pass themselves: that way they
                would be the visual parents of this dialog.
        """
        if not parent:
            parent = self

        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        current_tags = self.msgr.get_tags(task)
        tag_choices = [X for X in all_tags if X not in current_tags]

        artd = AddRemoveTagDialog(parent, task, current_tags, tag_choices=tag_choices)
        if artd.exec_() == QDialog.Accepted:
            cmd, new_tag = artd.return_values
            if cmd == "add":
                if len(new_tag) == 0:
                    pass  # user is not adding a tag
                elif new_tag in current_tags:
                    pass  # already have that tag
                # an actual new tag for this task (though it may exist already)
                else:
                    try:
                        self.msgr.add_single_tag(task, new_tag)
                        log.debug('tagging paper "%s" with "%s"', task, new_tag)
                    except PlomBadTagError as e:
                        ErrorMessage(f"Tag not acceptable: {e}").exec_()
            elif cmd == "remove":
                try:
                    self.msgr.remove_single_tag(task, new_tag)
                except PlomBadTagError as e:
                    ErrorMessage(f"Problem removing tag: {e}").exec_()
            else:
                # do nothing - shouldn't arrive here.
                pass

            # refresh the tags
            current_tags = self.msgr.get_tags(task)

            try:
                self.examModel.setTagsByTask(task, current_tags)
                self.ui.tableView.resizeColumnsToContents()
                self.ui.tableView.resizeRowsToContents()
            except ValueError:
                # we might not own the task for which we've have been managing tags
                pass

    def setFilter(self):
        """Sets a filter tag."""
        self.prxM.setFilterString(self.ui.filterLE.text().strip())
        # check to see if invert-filter is checked
        if self.ui.filterInvCB.checkState() == Qt.Checked:
            self.prxM.filterTags(invert=True)
        else:
            self.prxM.filterTags()

    def view_testnum_question(self):
        """shows the image."""
        tgs = SelectTestQuestion(self, self.exam_spec, self.question)
        if tgs.exec_() != QDialog.Accepted:
            return
        tn = tgs.tsb.value()
        gn = tgs.gsb.value()
        task = f"q{tn:04}g{gn}"
        try:
            imageList = self.msgr.MrequestOriginalImages(task)
        except PlomNoMoreException:
            msg = ErrorMessage(f"No image corresponding to task {task}")
            msg.exec_()
            return
        ifilenames = []
        for img_bytes in imageList:
            img_ext = imghdr.what(None, h=img_bytes)
            with tempfile.NamedTemporaryFile(
                "wb", dir=self.workingDirectory, suffix=f".{img_ext}", delete=False
            ) as f:
                f.write(img_bytes)
                ifilenames.append(f.name)
        qvmap = self.msgr.getQuestionVersionMap(tn)
        ver = qvmap[gn]
        QuestionViewDialog(self, ifilenames, tn, gn, ver=ver, marker=self).exec_()
