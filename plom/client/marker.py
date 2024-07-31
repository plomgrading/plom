# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Lior Silberman
# Copyright (C) 2024 Bryan Tanady

"""The Plom Marker client."""

from __future__ import annotations

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from collections import defaultdict
import html
import json
import logging
from math import ceil
from pathlib import Path
import platform
import queue
import random
import sys
import tempfile
from textwrap import shorten
import time
import threading
from typing import Any

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

from packaging.version import Version


from PyQt6 import uic, QtGui
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QThread,
    pyqtSlot,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from plom import __version__
import plom.client.ui_files
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomBadTagError,
    PlomBenignException,
    PlomForceLogoutException,
    PlomRangeException,
    PlomVersionMismatchException,
    PlomSeriousException,
    PlomTakenException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
    PlomConflict,
    PlomException,
    PlomNoPaper,
    PlomNoServerSupportException,
    PlomNoSolutionException,
)
from plom.messenger import Messenger
from plom.feedback_rules import feedback_rules as static_feedback_rules_data
from plom.question_labels import (
    get_question_label,
    verbose_question_label,
    check_for_shared_pages,
)
from .annotator import Annotator
from .image_view_widget import ImageViewWidget
from .viewers import QuestionViewDialog, SelectPaperQuestion
from .tagging import AddRemoveTagDialog
from .useful_classes import ErrorMsg, WarnMsg, InfoMsg, SimpleQuestion
from .tagging_range_dialog import TaggingAndRangeOptions
from .task_model import MarkerExamModel, ProxyModel


if platform.system() == "Darwin":
    # apparently needed for shortcuts under macOS
    from PyQt6.QtGui import qt_set_sequence_auto_mnemonic

    qt_set_sequence_auto_mnemonic(True)


log = logging.getLogger("marker")


def task_id_str_to_paper_question_index(task: str) -> tuple[int, int]:
    """Helper function to convert between task string and paper/question."""
    # TODO: I dislike this packed-string: overdue for refactor
    assert task[0] == "q", f"invalid task code {task}: no leading 'q'"
    assert task[5] == "g", f"invalid task code {task}: no middle 'g'"
    papernum = int(task[1:5])
    question_idx = int(task[6:])
    return papernum, question_idx


def paper_question_index_to_task_id_str(papernum: int, question_idx: int) -> str:
    """Helper function to convert between paper/question and task string."""
    return f"q{papernum:04}g{question_idx}"


class BackgroundUploader(QThread):
    """Uploads exams in Background."""

    uploadSuccess = pyqtSignal(str, int, int)
    uploadKnownFail = pyqtSignal(str, str)
    uploadUnknownFail = pyqtSignal(str, str)
    queue_status_changed = pyqtSignal(int, int, int, int)

    def __init__(self, msgr: Messenger) -> None:
        """Initialize a new uploader.

        Args:
            msgr: a Messenger for communicating with a Plom server.
                Note Messenger is not multithreaded and blocks using
                mutexes.  Here we make our own private clone so caller
                can keep using their's.
        """
        super().__init__()
        self.q: queue.Queue = queue.Queue()
        self.is_upload_in_progress = False
        self._msgr = Messenger.clone(msgr)
        self.num_uploaded = 0
        self.num_failed = 0
        self.simulate_failures = False
        # percentage of download attempts that will fail and an overall
        # delay in seconds in a range (both are i.i.d. per retry).
        # These are ignored unless simulate_failures is True.
        self._simulate_failure_rate = 20.0
        self._simulate_slow_net = (3, 8)

    def enable_fail_mode(self) -> None:
        log.info("fail mode ENABLED")
        self.simulate_failures = True

    def disable_fail_mode(self) -> None:
        log.info("fail mode disabled")
        self.simulate_failures = False

    def enqueueNewUpload(self, *args) -> None:
        """Places something in the upload queue.

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
        n = 1 if self.is_upload_in_progress else 0
        self.queue_status_changed.emit(
            self.q.qsize(), n, self.num_uploaded, self.num_failed
        )

    def queue_size(self) -> int:
        """Return the number of papers waiting or currently uploading."""
        if self.is_upload_in_progress:
            return self.q.qsize() + 1
        return self.q.qsize()

    def isEmpty(self) -> bool:
        """Checks if the upload queue is empty.

        Returns:
            True if the upload queue is empty, false otherwise.
        """
        # return self.q.empty()
        return self.queue_size() == 0

    def run(self) -> None:
        """Runs the uploader in background.

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
            log.info("upQ thread: popped code %s from queue, uploading", code)
            self.queue_status_changed.emit(
                self.q.qsize(), 1, self.num_uploaded, self.num_failed
            )
            simfail = False  # pylint worries it could be undefined
            if self.simulate_failures:
                simfail = random.random() <= self._simulate_failure_rate / 100
                a, b = self._simulate_slow_net
                # generate wait1 + wait2 \in (a, b)
                wait = random.random() * (b - a) + a
                time.sleep(wait)
            if self.simulate_failures and simfail:
                self.uploadUnknownFail.emit(code, "Simulated upload failure!")
                self.num_failed += 1
            else:
                if upload(
                    self._msgr,
                    *data,
                    knownFailCallback=self.uploadKnownFail.emit,
                    unknownFailCallback=self.uploadUnknownFail.emit,
                    successCallback=self.uploadSuccess.emit,
                ):
                    self.num_uploaded += 1
                else:
                    self.num_failed += 1
            self.is_upload_in_progress = False
            self.queue_status_changed.emit(
                self.q.qsize(), 0, self.num_uploaded, self.num_failed
            )

        log.info("upQ thread: starting with new empty queue and starting timer")
        # TODO: Probably don't need the timer: after each enqueue, signal the
        # QThread (in the new thread's event loop) to call tryToUpload.
        timer = QTimer()
        timer.timeout.connect(tryToUpload)
        timer.start(250)
        self.exec()


def upload(
    _msgr,
    task,
    grade,
    filenames,
    marking_time,
    question_idx,
    ver,
    rubrics,
    integrity_check,
    knownFailCallback=None,
    unknownFailCallback=None,
    successCallback=None,
):
    """Uploads a paper.

    Args:
        task (str): the Task ID for the page being uploaded. Takes the form
            "q1234g9" = test 1234 question 9.
        grade (int): grade given to question.
        filenames (list[str]): a list containing the annotated file's name,
            the .plom file's name and the comment file's name, in that order.
        marking_time (float/int): the marking time (s) for this specific question.
        question_idx (int or str): the question index number.
        ver (int or str): the version number.
        rubrics: list of rubrics used.
        integrity_check (str): the integrity_check string of the task.
        knownFailCallback: if we fail in a way that is reasonably expected,
            call this function.
        unknownFailCallback: if we fail but don't really know why or what
            do to, call this function.
        successCallback: a function to call when we succeed.

    Returns:
        bool: True for success, False for failure (either of the two).

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
            question_idx,
            ver,
            grade,
            marking_time,
            aname,
            pname,
            rubrics,
            integrity_check,
        )
    except (PlomTaskChangedError, PlomTaskDeletedError, PlomConflict) as ex:
        knownFailCallback(task, str(ex))
        # probably previous call does not return: it forces a crash
        return False
    except PlomException as ex:
        unknownFailCallback(task, str(ex))
        return False

    numDone = msg[0]
    numTotal = msg[1]
    successCallback(task, numDone, numTotal)
    return True


class MarkerClient(QWidget):
    """Setup for marking client and annotator.

    Notes:
        TODO: should be a QMainWindow but at any rate not a Dialog
        TODO: should this be parented by the QApplication?
    """

    my_shutdown_signal = pyqtSignal(int, list)

    def __init__(self, Qapp, tmpdir=None):
        """Initialize a new MarkerClient.

        Args:
            Qapp(QApplication): Main client application
            tmpdir (pathlib.Path/str/None): a temporary directory for
                storing image files and other data.  In principle can
                be shared with Identifier although this may not be
                implemented.  If `None`, we will make our own.
        """
        super().__init__()
        self.Qapp = Qapp

        uic.loadUi(resources.files(plom.client.ui_files) / "marker.ui", self)
        # TODO: temporary workaround
        self.ui = self
        # Keep the original format around in case we need to change it
        self._cachedProgressFormatStr = self.ui.mProgressBar.format()

        # Save the local temp directory for image files and the class list.
        if not tmpdir:
            tmpdir = tempfile.mkdtemp(prefix="plom_")
        self.workingDirectory = Path(tmpdir)
        log.debug("Working directory set to %s", self.workingDirectory)

        self.maxMark = -1  # temp value
        self.downloader = self.Qapp.downloader
        if self.downloader:
            # for unit tests, we might mockup Qapp.downloader as None
            # (Marker will not be functional without a downloader)
            self.downloader.download_finished.connect(self.background_download_finished)
            self.downloader.download_failed.connect(self.background_download_failed)
            self.downloader.download_queue_changed.connect(self.update_technical_stats)

        self.examModel = (
            MarkerExamModel()
        )  # Exam model for the table of groupimages - connect to table
        self.prxM = ProxyModel()  # set proxy for filtering and sorting
        # A view window for the papers so user can zoom in as needed.
        self.testImg = ImageViewWidget(self, has_rotate_controls=False)
        # A view window for the papers so user can zoom in as needed.
        self.ui.paperBoxLayout.addWidget(self.testImg, 10)

        # settings variable for annotator settings (initially None)
        self.annotatorSettings = defaultdict(lambda: None)
        self.commentCache = {}  # cache for Latex Comments
        self.backgroundUploader = None

        self.allowBackgroundOps = True

        # instance vars that get initialized later
        self.question_idx = None
        self.version = None
        self.exam_spec = None
        self.max_papernum = None

        self.msgr = None
        # history contains all the tgv in order of being marked except the current one.
        self.marking_history = []
        self._cachedProgressFormatStr = None

    def setup(
        self,
        messenger: Messenger,
        question_idx: int,
        version: int,
        lastTime: dict[str, Any],
    ) -> None:
        """Performs setup procedure for markerClient.

        TODO: move all this into init?

        TODO: verify all lastTime Params, there are almost certainly some missing

        Args:
            messenger: handle communication with server.
            question_idx: question index number, one based.
            version: question version number
            lastTime: dict of settings.
                Containing::

                   {
                     "FOREGROUND"
                     "KeyBinding"
                   }

                and potentially others

        Returns:
            None
        """
        self.msgr = messenger
        self.question_idx = question_idx
        self.version = version

        # Get the number of Tests, Pages, Questions and Versions
        # Note: if this fails UI is not yet in a usable state
        self.exam_spec = self.msgr.get_spec()

        self.UIInitialization()
        self.applyLastTimeOptions(lastTime)
        self.connectGuiButtons()

        # self.maxMark = self.exam_spec["question"][str(question_idx)]["mark"]
        try:
            self.maxMark = self.msgr.getMaxMark(self.question_idx)
        except PlomRangeException as err:
            ErrorMsg(self, str(err)).exec()
            return

        if not self.msgr.is_legacy_server():
            assert self.msgr.username
            self.annotatorSettings["nextTaskPreferTagged"] = "@" + self.msgr.username
        self.update_get_next_button()

        # Get list of papers already marked and add to table.
        if self.msgr.is_legacy_server():
            self.loadMarkedList()
        self.refresh_server_data()

        # Connect the view **after** list updated.
        # Connect the table-model's selection change to Marker functions
        self.ui.tableView.selectionModel().selectionChanged.connect(
            self.updatePreviewImage
        )
        self.ui.tableView.selectionModel().selectionChanged.connect(
            self.ensureAllDownloaded
        )

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
            self.backgroundUploader.queue_status_changed.connect(
                self.update_technical_stats_upload
            )
            self.backgroundUploader.start()
        self.cacheLatexComments()  # Now cache latex for comments:
        s = check_for_shared_pages(self.exam_spec, self.question_idx)
        if s:
            InfoMsg(self, s).exec()

    def applyLastTimeOptions(self, lastTime: dict[str, Any]) -> None:
        """Applies all settings from previous client.

        Args:
            lastTime (dict): information about settings, often from a
            config file such as from the last time the client was run.

        Returns:
            None
        """
        # TODO: some error handling here for users who hack their config?
        self.annotatorSettings["keybinding_name"] = lastTime.get("KeyBinding")
        self.annotatorSettings["keybinding_custom_overlay"] = lastTime.get("CustomKeys")

        if lastTime.get("FOREGROUND", False):
            self.allowBackgroundOps = False

    def is_experimental(self):
        return self.annotatorSettings["experimental"]

    def set_experimental(self, x):
        # TODO: maybe signals/slots should be used to watch for changes
        if x:
            log.info("Experimental/advanced mode enabled")
            self.annotatorSettings["experimental"] = True
        else:
            log.info("Experimental/advanced mode disabled")
            self.annotatorSettings["experimental"] = False

    def UIInitialization(self) -> None:
        """Startup procedure for the user interface.

        Returns:
            None: Modifies self.ui
        """
        self.setWindowTitle('Plom Marker: "{}"'.format(self.exam_spec["name"]))
        try:
            question_label = get_question_label(self.exam_spec, self.question_idx)
        except (ValueError, KeyError):
            question_label = "???"
        self.ui.labelTasks.setText(
            "Marking {} (ver. {}) of “{}”".format(
                question_label, self.version, self.exam_spec["name"]
            )
        )

        self.prxM.setSourceModel(self.examModel)
        self.ui.tableView.setModel(self.prxM)

        # Double-click or signal fires up the annotator window
        self.ui.tableView.doubleClicked.connect(self.annotateTest)
        self.ui.tableView.annotateSignal.connect(self.annotateTest)
        self.ui.tableView.tagSignal.connect(self.manage_tags)
        self.ui.tableView.claimSignal.connect(self.claim_task)
        self.ui.tableView.deferSignal.connect(self.defer_task)
        self.ui.tableView.reassignSignal.connect(self.reassign_task)

        if Version(__version__).is_devrelease:
            self.ui.technicalButton.setChecked(True)
            self.ui.failmodeCB.setEnabled(True)
        else:
            self.ui.technicalButton.setChecked(False)
            self.ui.failmodeCB.setEnabled(False)
        # if we want it to look like a label
        # self.ui.technicalButton.setStyleSheet("QToolButton { border: none; }")
        self.show_hide_technical()
        # self.force_update_technical_stats()
        self.update_technical_stats_upload(0, 0, 0, 0)

    def connectGuiButtons(self) -> None:
        """Connect gui buttons to appropriate functions.

        Notes:
            TODO: remove the total-radiobutton

        Returns:
            None but modifies self.ui
        """
        self.ui.closeButton.clicked.connect(self.close)
        m = QMenu(self)
        s = "Get \N{MATHEMATICAL ITALIC SMALL N}th..."
        m.addAction(s, self.claim_task_interactive)
        m.addAction("Which papers...", self.change_tag_range_options)
        self.ui.getNextButton.setMenu(m)
        self.ui.getNextButton.clicked.connect(self.requestNext)
        self.ui.annButton.clicked.connect(self.annotateTest)
        m = QMenu(self)
        # TODO: once enabled we don't need the explicit QAction
        # m.addAction("Reassign task to...", self.reassign_task)
        m.addAction("Claim task for me", self.claim_task)
        self.ui.deferButton.setMenu(m)
        self.ui.deferButton.clicked.connect(self.defer_task)
        self.ui.tasksComboBox.activated.connect(self.change_task_view)
        self.ui.refreshTaskListButton.clicked.connect(self.refresh_server_data)
        self.ui.refreshTaskListButton.setText("\N{CLOCKWISE OPEN CIRCLE ARROW}")
        self.ui.refreshTaskListButton.setToolTip("Refresh server data")
        self.ui.tagButton.clicked.connect(self.manage_tags)
        self.ui.filterLE.returnPressed.connect(self.setFilter)
        self.ui.filterLE.textEdited.connect(self.setFilter)
        self.ui.filterInvCB.stateChanged.connect(self.setFilter)
        self.ui.viewButton.clicked.connect(self.choose_and_view_other)
        self.ui.technicalButton.clicked.connect(self.show_hide_technical)
        self.ui.failmodeCB.stateChanged.connect(self.toggle_fail_mode)

    def change_tag_range_options(self):
        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        r = (
            self.annotatorSettings["nextTaskMinPaperNum"],
            self.annotatorSettings["nextTaskMaxPaperNum"],
        )
        tag = self.annotatorSettings["nextTaskPreferTagged"]
        mytag = "@" + self.msgr.username
        if tag == mytag:
            prefer_tagged_for_me = True
            tag = ""
        else:
            prefer_tagged_for_me = False
        d = TaggingAndRangeOptions(self, prefer_tagged_for_me, tag, all_tags, *r)
        if not d.exec():
            return
        r = d.get_papernum_range()
        tag = d.get_preferred_tag(self.msgr.username)
        self.annotatorSettings["nextTaskMinPaperNum"] = r[0]
        self.annotatorSettings["nextTaskMaxPaperNum"] = r[1]
        self.annotatorSettings["nextTaskPreferTagged"] = tag
        self.update_get_next_button()

    def update_get_next_button(self):
        tag = self.annotatorSettings["nextTaskPreferTagged"]
        mn = self.annotatorSettings["nextTaskMinPaperNum"]
        mx = self.annotatorSettings["nextTaskMaxPaperNum"]
        exclaim = False
        tips = []
        if mn is not None or mx is not None:
            exclaim = True
            s = "Restricted paper number "
            if mx is None:
                s += f"\N{GREATER-THAN OR EQUAL TO} {mn}"
            elif mn is None:
                s += f"\N{LESS-THAN OR EQUAL TO} {mx}"
            else:
                s += f"in [{mn}, {mx}]"
            tips.append(s)
        if tag:
            tips.append(f'prefer tagged "{tag}"')

        button_text = "&Get next"
        if exclaim:
            button_text += " (!)"
        self.getNextButton.setText(button_text)
        self.getNextButton.setToolTip("\n".join(tips))

    def loadMarkedList(self):
        """Loads the list of previously marked papers into self.examModel.

        Returns:
            None

        Deprecated: only called on legacy servers.

        Note: this tries to update the history between sessions; we don't
        try to do that on the new server, partially b/c the ordering seems
        fragile and I'm not sure its necessary.
        """
        # Ask server for list of previously marked papers
        markedList = self.msgr.MrequestDoneTasks(self.question_idx, self.version)
        self.marking_history = []
        for x in markedList:
            # TODO: might not the "markedList" have some other statuses?
            self.examModel.add_task(
                x[0],
                src_img_data=[],
                status="marked",
                mark=x[1],
                marking_time=x[2],
                tags=x[3],
                integrity_check=x[4],
                username=self.msgr.username,
            )
            self.marking_history.append(x[0])

    def get_files_for_previously_annotated(self, task: str) -> bool:
        """Loads the annotated image, the plom file, and the original source images.

        TODO: maybe it could not aggressively download the src images: sometimes
        people just want to look at the annotated image.

        Args:
            task (str): the task for the image files to be loaded from.
                Takes the form "q1234g9" = test 1234 question 9

        Returns:
            bool: currently this returns True.  Unless it fails which will
            induce a crash (after some popup dialogs).

        Raises:
            Uses error dialogs; not currently expected to throw exceptions
        """
        if len(self.examModel.get_source_image_data(task)) > 0:
            return True

        num, question_idx = task_id_str_to_paper_question_index(task)
        assert question_idx == self.question_idx, f"wrong qidx={question_idx}"

        # TODO: this integrity is almost certainly not important unless I want
        # to modify.  If just looking...?  Anyway, non-legacy doesn't enforce it
        integrity = self.examModel.getIntegrityCheck(task)
        try:
            plomdata = self.msgr.get_annotations(
                num, question_idx, edition=None, integrity=integrity
            )
            annot_img_info, annot_img_bytes = self.msgr.get_annotations_image(
                num, question_idx, edition=plomdata["annotation_edition"]
            )
        except PlomNoPaper as e:
            ErrorMsg(None, f"no annotations for task {task}: {e}").exec()
            # TODO: need something more significant to happen
            return True
        except (PlomTaskChangedError, PlomTaskDeletedError) as ex:
            # TODO: better action we can take here?
            # TODO: the real problem here is that the full_pagedata is potentially out of date!
            # TODO: we also need (and maybe already have) a mechanism to invalidate existing annotations
            # TODO: Issue #2146, parent=self will cause Marker to popup on top of Annotator
            ErrorMsg(
                None,
                '<p>The task "{}" has changed in some way by the manager; it '
                "may need to be remarked.</p>\n\n"
                '<p>Specifically, the server says: "{}"</p>\n\n'
                "<p>This is a rare situation; just in case, we'll now force a "
                "shutdown of your client.  Sorry.</p>"
                "<p>Please log back in and continue marking.</p>".format(task, str(ex)),
            ).exec()
            # Log out the user and then raise an exception
            try:
                self.msgr.closeUser()
            except PlomAuthenticationException:
                log.warning("We tried to logout user but they were already logged out.")
                pass
            # exit with code that is not 0 or 1
            self.Qapp.exit(57)
            log.critical("Qapp.exit() may not exit immediately; force quitting...")
            raise PlomForceLogoutException("Manager changed task") from ex

        log.info("importing source image data (orientations etc) from .plom file")
        # filenames likely stale: could have restarted client in meantime
        src_img_data = plomdata["base_images"]
        for row in src_img_data:
            # remove legacy "local_filename" if present
            f = row.pop("local_filename", None) or row.get("filename")
            if not row.get("server_path"):
                # E.g., Reannotator used to lose "server_path", keep workaround
                # just in case, by using previous session's filename
                row["server_path"] = f
        self.get_downloads_for_src_img_data(src_img_data)

        self.examModel.set_source_image_data(task, src_img_data)

        assert task.startswith("q")
        paperdir = Path(
            tempfile.mkdtemp(prefix=task[1:] + "_", dir=self.workingDirectory)
        )
        log.debug("create paperdir %s for already-graded download", paperdir)
        self.examModel.setPaperDirByTask(task, paperdir)
        aname = paperdir / f"G{task[1:]}.{annot_img_info['extension']}"
        pname = paperdir / f"G{task[1:]}.plom"
        with open(aname, "wb") as fh:
            fh.write(annot_img_bytes)
        with open(pname, "w") as f:
            json.dump(plomdata, f, indent="  ")
            f.write("\n")
        self.examModel.setAnnotatedFile(task, aname, pname)
        return True

    def _updateImage(self, pr: int) -> None:
        """Updates the preview image for a particular row of the table.

        Try various things to get an appropriate image to display.
        Lots of side effects as we update the table as needed.

        .. note::
           This function is a workaround used to keep the preview
           up-to-date as the table of papers changes.  Ideally
           the two widgets would be linked with some slots/signals
           so that they were automatically in-sync and updates to
           the table would automatically reload the preview.  Perhaps
           some future Qt expert will help us...

        Args:
            pr: which row is highlighted, via row index.

        Returns:
            None
        """
        # simplest first: if we have the annotated image then display that
        ann_img_file = self.prxM.getAnnotatedFile(pr)
        # TODO: special hack as empty "" comes back as Path which is "."
        if str(ann_img_file) == ".":
            ann_img_file = ""
        if ann_img_file:
            self.testImg.updateImage(ann_img_file)
            return

        task = self.prxM.getPrefix(pr)
        status = self.prxM.getStatus(pr)

        # next we try to download annotated image for certain hardcoded states
        if status.casefold() in ("complete", "marked"):
            # Note: "marked" is only on legacy servers
            self.get_files_for_previously_annotated(task)
            self._updateImage(pr)  # recurse
            return

        # try the raw page images instead from the cached src_img_data
        src_img_data = self.examModel.get_source_image_data(task)
        if src_img_data:
            self.get_downloads_for_src_img_data(src_img_data)
            self.testImg.updateImage(src_img_data)
            return

        # but if the src_img_data isn't present, get and trigger background downloads
        src_img_data = self.get_src_img_data(task, cache=True)
        if src_img_data:
            self.get_downloads_for_src_img_data(src_img_data)
            self.testImg.updateImage(src_img_data)

        # All else fails, just wipe the display (e.g., pages removed from server)
        self.testImg.updateImage(None)

    def get_src_img_data(
        self, task: str, *, cache: bool = False
    ) -> list[dict[str, Any]]:
        """Download the pagedate/src_img_data for a particular task.

        Note this does not trigger downloads of the page images.  For
        that, see :method:`get_downloads_for_src_img_data`.

        Args:
            task: which task to download the page data for.

        Keyword Args:
            cache: if this is one of the questions that we're marking,
                also fill-in or update the client-side cache of pagedata.
                Caution: page-arranger might mess with the local copy,
                so for now be careful using this option.  Default: False.

        Returns:
            The source image data.

        Raises:
            PlomConflict: no paper.
        """
        papernum, qidx = task_id_str_to_paper_question_index(task)
        pagedata = self.msgr.get_pagedata_context_question(papernum, qidx)

        # TODO: is this the main difference between pagedata and src_img_data?
        pagedata = [x for x in pagedata if x["included"]]

        if cache and self.question_idx == qidx:
            try:
                self.examModel.set_source_image_data(task, pagedata)
            except KeyError:
                pass
        return pagedata

    def _updateCurrentlySelectedRow(self) -> None:
        """Updates the preview image for the currently selected row of the table.

        Returns:
            None
        """
        prIndex = self.ui.tableView.selectedIndexes()
        if len(prIndex) == 0:
            return
        # Note: a single selection should have length 11: could assert
        pr = prIndex[0].row()
        self._updateImage(pr)

    def updateProgress(self, val=None, maxm=None) -> None:
        """Updates the progress bar.

        Args:
            val (int): value for the progress bar
            maxm (int): maximum for the progress bar.

        Returns:
            None
        """
        if not val and not maxm:
            # ask server for progress update
            try:
                val, maxm = self.msgr.MprogressCount(self.question_idx, self.version)
            except PlomRangeException as e:
                ErrorMsg(self, str(e)).exec()
                return
        if maxm == 0:
            val, maxm = (0, 1)  # avoid (0, 0) indeterminate animation
            self.ui.mProgressBar.setFormat("No papers to mark")
            try:
                qlabel = get_question_label(self.exam_spec, self.question_idx)
                verbose_qlabel = verbose_question_label(
                    self.exam_spec, self.question_idx
                )
            except (ValueError, KeyError):
                qlabel = "???"
                verbose_qlabel = qlabel
            msg = f"<p>Currently there is nothing to mark for version {self.version}"
            msg += f" of {verbose_qlabel}.</p>"
            info = f"""<p>There are several ways this can happen:</p>
                <ul>
                <li>Perhaps the relevant papers have not yet been scanned.</li>
                <li>This assessment may not have instances of version
                    {self.version} of {qlabel}.</li>
                </ul>
            """
            InfoMsg(self, msg, info=info, info_pre=False).exec()
        else:
            # Neither is quite right, instead, we cache on init
            self.ui.mProgressBar.setFormat(self._cachedProgressFormatStr)
        self.ui.mProgressBar.setMaximum(maxm)
        self.ui.mProgressBar.setValue(val)

    def claim_task_interactive(self) -> None:
        """Ask user for paper number and then ask server for that paper.

        If available, download stuff, add to list, update view.
        """
        verbose_qlabel = verbose_question_label(self.exam_spec, self.question_idx)
        s = "<p>Which paper number would you like to get?</p>"
        s += f"<p>Note: you are marking version {self.version}"
        s += f" of {verbose_qlabel}.</p>"
        n, ok = QInputDialog.getInt(
            self, "Which paper to get", s, 1, 1, self.max_papernum
        )
        if not ok:
            return
        task = f"q{n:04}g{self.question_idx}"
        self._claim_task(task)

    def requestNext(self, *, update_select=True):
        """Ask server for an unmarked paper, get file, add to list, update view.

        Retry a few times in case two clients are asking for same.

        Keyword Args:
            update_select (bool): default True, send False if you don't
                want to adjust the visual selection.

        Returns:
            None
        """
        attempts = 0
        tag = self.annotatorSettings["nextTaskPreferTagged"]
        paper_range = (
            self.annotatorSettings["nextTaskMinPaperNum"],
            self.annotatorSettings["nextTaskMaxPaperNum"],
        )
        if tag and (paper_range[0] or paper_range[1]):
            log.info('Next available?  Range %s, prefer tagged "%s"', paper_range, tag)
        elif tag:
            log.info('Next available?  Prefer tagged "%s"', tag)
        elif paper_range[0] or paper_range[1]:
            log.info("Next available?  Range %s", paper_range)
        if tag:
            tags = [tag]
        else:
            tags = []
        while True:
            attempts += 1
            # little sanity check - shouldn't be needed.
            # TODO remove.
            if attempts > 5:
                return
            try:
                task = self.msgr.MaskNextTask(
                    self.question_idx,
                    self.version,
                    tags=tags,
                    min_paper_num=paper_range[0],
                    max_paper_num=paper_range[1],
                )
                if not task:
                    return
            except PlomSeriousException as err:
                log.exception("Unexpected error getting next task: %s", err)
                # TODO: Issue #2146, parent=self will cause Marker to popup on top of Annotator
                ErrorMsg(
                    None,
                    "Unexpected error getting next task. Client will now crash!",
                    info=err,
                ).exec()
                raise

            try:
                self.claim_task_and_trigger_downloads(task)
                break
            except PlomTakenException as err:
                log.info("will keep trying as task already taken: {}".format(err))
                continue
        if update_select:
            self.moveSelectionToTask(task)

    def get_downloads_for_src_img_data(self, src_img_data, trigger=True):
        """Make sure the images for some source image data are downloaded.

        If an image is not yet downloaded, trigger the download again.

        Args:
            src_img_data (list): list of dicts.  Note we may modify this
                so pass a copy if you don't want this!  Specifically,
                the ``"filename"`` key is inserted or replaced with the
                path to the downloaded image or the placeholder image.

        Keyword Args:
            trigger (bool): if True we trigger background jobs for any
                that have not been downloaded.

        Returns:
            bool: True if all images have already been downloaded, False
            if at least one was not.  In the False case, downloads have
            been triggered; wait; process events; then call back if you
            want.
        """
        all_present = True
        PC = self.downloader.pagecache
        for row in src_img_data:
            if PC.has_page_image(row["id"]):
                row["filename"] = PC.page_image_path(row["id"])
                continue
            all_present = False
            log.info("triggering download for image id %d", row["id"])
            self.downloader.download_in_background_thread(row)
            row["filename"] = self.downloader.get_placeholder_path()
        return all_present

    def claim_task_and_trigger_downloads(self, task: str) -> None:
        """Claim a particular task for the current user and start image downloads.

        Notes:
            Side effects: on success, updates the table of tasks by adding
            a new row (or modifying an existing one).  But the new row is
            *not* automatically selected.

        Returns:
            None

        Raises:
            PlomTakenException
            PlomVersionMismatchException
        """
        _, qidx = task_id_str_to_paper_question_index(task)
        assert qidx == self.question_idx, f"wrong question: question_idx={qidx}"
        src_img_data, tags, integrity_check = self.msgr.MclaimThisTask(
            task, version=self.version
        )

        self.get_downloads_for_src_img_data(src_img_data)

        # TODO: do we really want to just hardcode "untouched" here?
        self.examModel.modify_task(
            task,
            src_img_data=src_img_data,
            status="untouched",
            mark=-1,
            marking_time=0.0,
            tags=tags,
            integrity_check=integrity_check,
            username=self.msgr.username,
        )

    def moveSelectionToTask(self, task):
        """Update the selection in the list of papers."""
        pr = self.prxM.rowFromTask(task)
        if pr is None:
            return
        self.ui.tableView.selectRow(pr)
        # this might redraw it twice: oh well this is not common operation
        self._updateCurrentlySelectedRow()
        # Clean up the table
        self.ui.tableView.resizeColumnsToContents()
        self.ui.tableView.resizeRowsToContents()

    def background_download_finished(self, img_id, md5, filename):
        log.debug(f"PageCache has finished downloading {img_id} to {filename}")
        self.ui.labelTech2.setText(f"last msg: downloaded img id={img_id}")
        self.ui.labelTech2.setToolTip(f"{filename}")
        # TODO: not all downloads require redrawing the current row...
        # if any("placeholder" in x for x in testImg.imagenames):
        # force a redraw
        self._updateCurrentlySelectedRow()

    def background_download_failed(self, img_id):
        """Callback when a nackground download has failed."""
        self.ui.labelTech2.setText(f"<p>last msg: failed download img id={img_id}</p>")
        log.info(f"failed download img id={img_id}")
        self.ui.labelTech2.setToolTip("")

    def force_update_technical_stats(self):
        stats = self.downloader.get_stats()
        self.update_technical_stats(stats)

    def update_technical_stats(self, d):
        self.ui.labelTech1.setText(
            "<p>"
            f"downloads: {d['queued']} queued, {d['cache_size']} cached,"
            f" {d['retries']} retried, {d['fails']} failed"
            "</p>"
        )

    def update_technical_stats_upload(self, n, m, numup, failed):
        if n == 0 and m == 0:
            txt = "upload: idle"
        else:
            txt = f"upload: {n} queued, {m} inprogress"
        txt += f", {numup} done, {failed} failed"
        self.ui.labelTech3.setText(txt)

    def show_hide_technical(self):
        """Toggle the technical panel in response to checking a button."""
        if self.ui.technicalButton.isChecked():
            self.ui.technicalButton.setText("Hide technical info")
            self.ui.technicalButton.setArrowType(Qt.ArrowType.DownArrow)
            self.ui.frameTechnical.setVisible(True)
            ptsz = self.ui.technicalButton.fontInfo().pointSizeF()
            self.ui.frameTechnical.setStyleSheet(
                f"QWidget {{ font-size: {0.7 * ptsz}pt; }}"
            )
            # future use
            self.ui.labelTech4.setVisible(False)
            # toggle various columns without end-user useful info
            for i in self.ui.examModel.columns_to_hide:
                self.ui.tableView.showColumn(i)
                # Limit the widths of the debugging columns, otherwise ridiculous
                # TODO: no initial effect (before view setModel, does self.setHorizontalHeaderLabels)

                self.ui.tableView.setColumnWidth(i, 128)
        else:
            self.ui.technicalButton.setText("Show technical info")
            self.ui.technicalButton.setArrowType(Qt.ArrowType.RightArrow)
            self.ui.frameTechnical.setVisible(False)
            for i in self.ui.examModel.columns_to_hide:
                self.ui.tableView.hideColumn(i)

    def toggle_fail_mode(self):
        """Toggle artificial failures simulatiing flaky networking in response to ticking a button."""
        if self.ui.failmodeCB.isChecked():
            self.Qapp.downloader.enable_fail_mode()
            r = self.Qapp.downloader._simulate_failure_rate
            a, b = self.Qapp.downloader._simulate_slow_net
            tip = f"download: delay ∈ [{a}s, {b}s], {r:0g}% retry"
            if self.allowBackgroundOps:
                self.backgroundUploader.enable_fail_mode()
                r = self.backgroundUploader._simulate_failure_rate
                a, b = self.backgroundUploader._simulate_slow_net
                tip += f"\nupload delay ∈ [{a}s, {b}s], {r:0g}% fail"
            self.ui.failmodeCB.setToolTip(tip)
        else:
            self.ui.failmodeCB.setToolTip("")
            self.Qapp.downloader.disable_fail_mode()
            if self.allowBackgroundOps:
                self.backgroundUploader.disable_fail_mode()

    def requestNextInBackgroundStart(self) -> None:
        """Requests the next TGV in the background.

        Returns:
            None
        """
        self.requestNext(update_select=False)

    def moveToNextUnmarkedTest(self, task: str | None = None) -> bool:
        """Move the list to the next unmarked test, if possible.

        Args:
            task: the task number of the next unmarked test.

        Returns:
            True if move was successful, False if not, for any reason.
        """
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
        while self.prxM.getStatus(pr).casefold() != "untouched":
            pr = (pr + 1) % prt
            if pr == prstart:  # don't get stuck in a loop
                break
        if pr == prstart:
            return False  # have looped over all rows and not found anything.
        self.ui.tableView.selectRow(pr)

        # Might need to wait for a background downloader.  Important to
        # processEvents() so we can receive the downloader-finished signal.
        task = self.prxM.getPrefix(pr)
        count = 0
        # placeholder = self.downloader.get_placeholder_path()
        while True:
            src_img_data = self.examModel.get_source_image_data(task)
            if self.get_downloads_for_src_img_data(src_img_data):
                break
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
                if msg.exec() == QMessageBox.StandardButton.No:
                    return False
                count = 0
                self.Qapp.processEvents()

        return True

    def change_task_view(self, cbidx: int) -> None:
        """Update task list in response to combobox activation.

        In some cases we reject the change and change the index ourselves.
        """
        if cbidx == 0:
            self._show_only_my_tasks()
            return
        if cbidx != 1:
            raise NotImplementedError(f"Unexpected cbidx={cbidx}")
        if not self.annotatorSettings["user_can_view_all_tasks"]:
            InfoMsg(self, "You don't have permission to view all tasks").exec()
            self.ui.tasksComboBox.setCurrentIndex(0)
            self._show_only_my_tasks()
            return
        self._show_all_tasks()
        if not self.download_task_list():
            # could not update (maybe legacy server) so go back to only mine
            self.ui.tasksComboBox.setCurrentIndex(0)
            self._show_only_my_tasks()

    def refresh_server_data(self):
        """Refresh various server data including the current task last from the server."""
        info = self.msgr.get_exam_info()
        self.max_papernum = info["current_largest_paper_num"]
        # legacy won't provide this; fallback to a static value
        self.annotatorSettings["feedback_rules"] = info.get(
            "feedback_rules", static_feedback_rules_data
        )
        # server says local defaults should be used if it sends empty
        if not self.annotatorSettings["feedback_rules"]:
            self.annotatorSettings["feedback_rules"] = static_feedback_rules_data
        if not self.msgr.is_legacy_server():
            # TODO: in future, I think I prefer a rules-based framework
            # Not "you are lead marker" but "you can view all tasks".
            # To my mind, "lead_marker" etc is some server detail that
            # could stay on the server.
            if self.msgr.get_user_role() == "lead_marker":
                self.annotatorSettings["user_can_view_all_tasks"] = True
            else:
                self.annotatorSettings["user_can_view_all_tasks"] = False
        else:
            self.annotatorSettings["user_can_view_all_tasks"] = False
        if not self.annotatorSettings["user_can_view_all_tasks"]:
            # it might've changed, so reset combobox selection
            self.ui.tasksComboBox.setCurrentIndex(0)
            self._show_only_my_tasks()

        # legacy does it own thing earlier in the workflow
        if not self.msgr.is_legacy_server():
            if self.ui.tasksComboBox.currentIndex() == 0:
                assert self.msgr.username is not None
                self.download_task_list(username=self.msgr.username)
            else:
                self.download_task_list()

        # TODO: re-queue any failed uploads, Issue #3497

        self.updateProgress()

    def download_task_list(self, *, username: str = "") -> bool:
        """Download and fill/update the task list.

        Danger: there is quite a bit of subtly here about how to update
        tasks when we already have local cached data or when the local
        state might be mid-upload.

        Keyword Args:
            username: find tasks assigned to this user, or all tasks if
                omitted.

        Returns:
            True if the donload was successful, False if the server
            does not support this.
        """
        try:
            tasks = self.msgr.get_tasks(
                self.question_idx, self.version, username=username
            )
        except PlomNoServerSupportException as e:
            WarnMsg(self, str(e)).exec()
            return False
        our_username = self.msgr.username
        for t in tasks:
            task_id_str = paper_question_index_to_task_id_str(
                t["paper_number"], t["question"]
            )
            username = t.get("username", "")
            integrity = t.get("integrity", "")
            # TODO: maybe task_model can support None for mark too...?
            mark = t.get("score", -1)  # not keen on this -1 sentinel
            status = t["status"]
            # mismatch b/w server status and how we represent claimed tasks locally
            if status.casefold() == "out" and username == our_username:
                status = "untouched"
            try:
                self.examModel.add_task(
                    task_id_str,
                    src_img_data=[],
                    mark=mark,
                    marking_time=t.get("marking_time", 0.0),
                    status=status,
                    tags=t["tags"],
                    username=username,
                    integrity_check=integrity,
                )
            except KeyError:
                if username != our_username:
                    # If server says its not our task, then overwrite local state
                    # b/c the task may have been reassigned.
                    # TODO: but this stomps on local cached annotation data, so that's wasteful
                    # TODO: use the integrity_check?
                    self.examModel.modify_task(
                        task_id_str,
                        src_img_data=[],
                        mark=mark,
                        marking_time=t.get("marking_time", 0.0),
                        status=status,
                        tags=t["tags"],
                        username=username,
                    )
                    continue
                # If it is our task, be careful b/c we don't want to stomp local state
                # such as downloaded images, in-progress uploads etc.
                # Currently we just keep the local state but this may not be correct
                # if server has changed something.  TODO: use the integrity_check
                # print(f"keeping local copy for {task_id_str}:\n\t{t}")
        return True

    def reassign_task(self):
        """TODO: just a stub for now, no one is calling this."""
        task = self.get_current_task_id_or_none()
        if not task:
            return
        # TODO: combobox
        assign_to, ok = QInputDialog.getText(
            self, "Reassign to", f"Who would you like to reassign {task} to?"
        )
        if not ok:
            return
        # try:
        #     self.msgr.TODO_New_Function(task, self.user, assign_to, reason="help")
        # except PlomNoServerSupportException as e:
        #     InfoMsg(self, e).exec()
        #     return
        # except PlomNoPermission as e:
        #     InfoMsg(self, "You don't have permission to reassign that task: {e}").exec()
        #     return
        if random.random() < 0.5:
            WarnMsg(
                self, f'TODO: faked error reassigning {task} to "{assign_to}"'
            ).exec()
            return
        InfoMsg(self, f'TODO: faked success reassigning {task} to "{assign_to}"').exec()
        # TODO, now what?
        # TODO: adding a new possibility here will have some fallout
        self.examModel.setStatusByTask(task, "reassigned")

    def claim_task(self) -> None:
        """Try to claim the currently selected task for this user."""
        task = self.get_current_task_id_or_none()
        if not task:
            return
        # TODO: if its "To Do" we can just claim it
        # TODO: in fact, I'd expect double-click to do that.
        user = self.examModel.get_username_by_task(task)
        if user == self.msgr.username:
            InfoMsg(
                self,
                f"Note: task {task} appears to already belong to you,"
                " trying to claim anyway...",
            ).exec()
        elif self.examModel.getStatusByTask(task).casefold() != "to do":
            WarnMsg(
                self, f'Not implemented yet: cannot claim {task} from user "{user}"'
            ).exec()
            return
        self._claim_task(task)

    def _claim_task(self, task: str) -> None:
        log.info("claiming task %s", task)
        try:
            self.claim_task_and_trigger_downloads(task)
        except (
            PlomTakenException,
            PlomRangeException,
            PlomVersionMismatchException,
        ) as err:
            WarnMsg(self, f"Cannot get task {task}.", info=err).exec()
            return
        # maybe it was there already: should be harmless
        self.moveSelectionToTask(task)

    def defer_task(self):
        """Mark task as "defer" - to be skipped until later."""
        task = self.get_current_task_id_or_none()
        if not task:
            return
        if self.examModel.getStatusByTask(task) == "deferred":
            return
        if not self.examModel.is_our_task(task, self.msgr.username):
            s = f"Cannot defer task {task} b/c it isn't yours"
            user = self.examModel.get_username_by_task(task)
            if user:
                s += f': {task} belongs to "{user}"'
            InfoMsg(self, s).exec()
            return
        if self.examModel.getStatusByTask(task).casefold() in (
            "complete",
            "marked",
            "uploading...",
            "failed upload",
        ):
            InfoMsg(self, "Cannot defer a marked test.").exec()
            return
        self.examModel.deferPaper(task)

    def startTheAnnotator(self, initialData) -> None:
        """This fires up the annotation window for user annotation + marking.

        Args:
            initialData (list): containing things documented elsewhere
                in :method:`getDataForAnnotator`
                and :func:`plom.client.annotator.Annotator.__init__`.

        Returns:
            None
        """
        annotator = Annotator(
            self.msgr.username,
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
        task = self.get_current_task_id_or_none()
        if not task:
            return
        if not self.examModel.is_our_task(task, self.msgr.username):
            InfoMsg(self, f"Cannot annotate {task}: it is not assigned to you").exec()
            return
        inidata = self.getDataForAnnotator(task)
        if inidata is None:
            InfoMsg(
                self,
                f"Cannot annotate {task},"
                " perhaps it is not assigned to you, or a download failed"
                " perhaps due to poor or missing internet connection.",
            ).exec()
            return

        if self.allowBackgroundOps:
            # If just one in the queue (which we are grading) then ask for more
            if self.examModel.countReadyToMark() <= 1:
                self.requestNextInBackgroundStart()

        self.startTheAnnotator(inidata)
        # we started the annotator, we'll get a signal back when its done

    def getDataForAnnotator(self, task: str) -> tuple | None:
        """Start annotator on a particular task.

        Args:
            task: the task id.  If original qXXXXgYY, then annotated
                version is GXXXXgYY (G=graded).

        Returns:
            A tuple of data or None.
        """
        status = self.examModel.getStatusByTask(task)

        if status.casefold() not in (
            "complete",
            "marked",
            "uploading...",
            "failed upload",
            "untouched",
            "deferred",
        ):
            # TODO: should this make a dialog somewhere?
            log.warn(f"task {task} status '{status}' is not your's to annotate")
            return None

        # Create annotated filename.
        assert task.startswith("q")
        paperdir = Path(
            tempfile.mkdtemp(prefix=task[1:] + "_", dir=self.workingDirectory)
        )
        log.debug("create paperdir %s for annotating", paperdir)
        Gtask = "G" + task[1:]
        # note no extension yet
        aname = paperdir / Gtask
        pdict = None

        if status.casefold() in ("complete", "marked", "uploading...", "failed upload"):
            msg = SimpleQuestion(self, "Continue marking paper?")
            if not msg.exec() == QMessageBox.StandardButton.Yes:
                return None
            oldpname = self.examModel.getPlomFileByTask(task)
            with open(oldpname, "r") as fh:
                pdict = json.load(fh)

        # Yes do this even for a regrade!  We will recreate the annotations
        # (using the plom file) on top of the original file.
        count = 0
        while True:
            if pdict:
                log.info("Taking src_img_data from previous plom data")
                src_img_data = pdict["base_images"]
            else:
                src_img_data = self.examModel.get_source_image_data(task)
            if self.get_downloads_for_src_img_data(src_img_data):
                break
            time.sleep(0.1)
            self.Qapp.processEvents()
            count += 1
            if (count % 10) == 0:
                log.info("waiting for downloader: {}".format(src_img_data))
            if count >= 40:
                msg = SimpleQuestion(
                    self,
                    "Still waiting for download.  Do you want to wait a bit longer?",
                )
                if msg.exec() == QMessageBox.StandardButton.No:
                    return None
                count = 0
                self.Qapp.processEvents()

        # maybe the downloader failed for some (rare) reason
        for data in src_img_data:
            if not Path(data["filename"]).exists():
                log.warning(
                    "some kind of downloader fail? (unexpected, but probably harmless"
                )
                return None

        # we used to set status to indicate annotation-in-progress; removed as
        # it doesn't seem necessary (it was tricky to set it back afterwards)

        exam_name = self.exam_spec["name"]

        papernum, question_idx = task_id_str_to_paper_question_index(task)
        taskid = task[1:]
        question_label = get_question_label(self.exam_spec, question_idx)
        integrity_check = self.examModel.getIntegrityCheck(task)
        return (
            taskid,
            question_label,
            self.version,
            self.exam_spec["numberOfVersions"],
            exam_name,
            paperdir,
            aname,
            self.maxMark,
            pdict,
            integrity_check,
            src_img_data,
        )

    def getRubricsFromServer(self, question: int | None = None) -> list[dict[str, Any]]:
        """Get list of rubrics from server.

        Args:
            question: pertaining to which question or ``None`` for all
                rubrics.

        Returns:
            A list of the dictionary objects.
        """
        return self.msgr.MgetRubrics(question)

    def getOneRubricFromServer(self, key: str) -> dict[str, Any]:
        """Get one rubric from server.

        Args:
            key: which rubric.

        Returns:
            Dictionary representation of the rubric..

        Raises:
            PlomNoRubric
        """
        return self.msgr.get_one_rubric(key)

    def getOtherRubricUsagesFromServer(self, key: str) -> list[int]:
        """Get list of paper numbers using the given rubric.

        Args:
            key: the identifier of the rubric.

        Returns:
            List of paper numbers using the rubric.
        """
        return self.msgr.MgetOtherRubricUsages(key)

    def sendNewRubricToServer(self, new_rubric) -> dict[str, Any]:
        return self.msgr.McreateRubric(new_rubric)

    def modifyRubricOnServer(self, key, updated_rubric) -> dict[str, Any]:
        return self.msgr.MmodifyRubric(key, updated_rubric)

    def getSolutionImage(self) -> Path | None:
        """Get the file from disc if it exists, else grab from server."""
        f = self.workingDirectory / f"solution.{self.question_idx}.{self.version}.png"
        if f.is_file():
            return f
        return self.refreshSolutionImage()

    def refreshSolutionImage(self) -> Path | None:
        """Get solution image and save it to working dir."""
        f = self.workingDirectory / f"solution.{self.question_idx}.{self.version}.png"
        try:
            im_bytes = self.msgr.getSolutionImage(self.question_idx, self.version)
            with open(f, "wb") as fh:
                fh.write(im_bytes)
            return f
        except PlomNoSolutionException as e:
            log.warning(f"no solution image: {e}")
            # if a residual file is there, try to delete it
            try:
                f.unlink()
            except FileNotFoundError:
                pass
            return None

    def saveTabStateToServer(self, tab_state):
        """Upload a tab state to the server."""
        log.info("Saving user's rubric tab configuration to server")
        self.msgr.MsaveUserRubricTabs(self.question_idx, tab_state)

    def getTabStateFromServer(self):
        """Download the state from the server."""
        log.info("Pulling user's rubric tab configuration from server")
        return self.msgr.MgetUserRubricTabs(self.question_idx)

    # when Annotator done, we come back to one of these callbackAnnDone* fcns
    @pyqtSlot(str)
    def callbackAnnDoneCancel(self, task: str) -> None:
        """Called when annotator is done grading.

        Args:
            task: task name without the leading "q".

        Returns:
            None
        """
        self.setEnabled(True)
        # update image view b/c its image might have changed
        self._updateCurrentlySelectedRow()

    @pyqtSlot(str)
    def callbackAnnDoneClosing(self, task: str) -> None:
        """Called when annotator is done grading and is closing.

        Args:
            task: the task ID of the current test with no leading "q".

        Returns:
            None
        """
        self.setEnabled(True)
        # update image view b/c its image might have changed
        self._updateCurrentlySelectedRow()

    @pyqtSlot(str, list)
    def callbackAnnWantsUsToUpload(self, task, stuff) -> None:
        """Called when annotator wants to upload.

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
        # TODO: this is probably the right time to insert the modified src_img_data
        # TODO: but it may not matter as now the plomFileName has it internally
        self.examModel.markPaperByTask(
            task, grade, aname, plomFileName, markingTime, paperDir
        )
        # update the markingTime to be the total marking time
        totmtime = self.examModel.get_marking_time_by_task(task)

        _data = (
            task,
            grade,
            (
                aname,
                plomFileName,
            ),
            totmtime,  # total marking time (seconds)
            self.question_idx,
            self.version,
            rubrics,
            integrity_check,
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
        # successfully marked and put on the upload list.
        # now update the marking history with the task.
        self.marking_history.append(task)

    def getMorePapers(self, oldtgvID: str) -> tuple | None:
        """Loads more tests.

        Args:
            oldtgvID: the task code with no leading "q" for the previous
                thing marked.

        Returns:
            The data for the annotator or None as described in
            :method:`getDataForAnnotator`.
        """
        log.debug("Annotator wants more (w/o closing)")
        if not self.allowBackgroundOps:
            self.requestNext(update_select=False)
        if not self.moveToNextUnmarkedTest("q" + oldtgvID if oldtgvID else None):
            return None
        task_id_str = self.get_current_task_id_or_none()
        if not task_id_str:
            return None
        data = self.getDataForAnnotator(task_id_str)
        if data is None:
            return None

        assert task_id_str[1:] == data[0]
        pdict = data[-3]  # the plomdict is third-last object in data
        assert pdict is None, "Annotator should not pull a regrade"

        if self.allowBackgroundOps:
            # If just one in the queue (which we are grading) then ask for more
            if self.examModel.countReadyToMark() <= 1:
                self.requestNextInBackgroundStart()

        return data

    def backgroundUploadFinished(self, task, numDone, numtotal) -> None:
        """An upload has finished, do appropriate UI updates.

        Args:
            task (str): the task ID of the current test.
            numDone (int): number of exams marked
            numtotal (int): total number of exams to mark.

        Returns:
            None
        """
        stat = self.examModel.getStatusByTask(task)
        # maybe it changed while we waited for the upload
        if stat == "uploading...":
            if self.msgr.is_legacy_server():
                self.examModel.setStatusByTask(task, "marked")
            else:
                self.examModel.setStatusByTask(task, "Complete")
        self.updateProgress(numDone, numtotal)

    def backgroundUploadFailedServerChanged(self, task, error_message):
        """An upload has failed because server changed something, safest to quit.

        Args:
            task (str): the task ID of the current test.
            error_message (str): a brief description of the error.

        Returns:
            None
        """
        self.examModel.setStatusByTask(task, "failed upload")
        # TODO: Issue #2146, parent=self will cause Marker to popup on top of Annotator
        ErrorMsg(
            None,
            '<p>Background upload of "{}" has failed because the server '
            "changed something underneath us.</p>\n\n"
            '<p>Specifically, the server says: "{}"</p>\n\n'
            "<p>This is a rare situation; no data corruption has occurred but "
            "your annotations have been discarded just in case.  You will be "
            "asked to redo the task later.</p>\n\n"
            "<p>For now you've been logged out and we'll now force a shutdown "
            "of your client.  Sorry.</p>"
            "<p>Please log back in and continue marking.</p>".format(
                task, error_message
            ),
        ).exec()
        # Log out the user and then raise an exception
        try:
            self.msgr.closeUser()
        except PlomAuthenticationException:
            log.warning("We tried to log out user but they were already logged out.")
            pass
        # exit with code that is not 0 or 1
        self.Qapp.exit(57)
        # raise PlomForceLogoutException(
        # "Server changed under us: {}".format(error_message)
        # ) from None

    def backgroundUploadFailed(self, task: str, errmsg: str) -> None:
        """An upload has failed, we don't know why, do something LOUDLY.

        Args:
            task (str): the task ID of the current test.
            errmsg (str): the error message.

        Returns:
            None
        """
        self.examModel.setStatusByTask(task, "failed upload")
        # TODO: Issue #2146, parent=self will cause Marker to popup on top of Annotator
        ErrorMsg(
            None,
            "Unfortunately, there was an unexpected error; the server did "
            f"not accept our marked paper {task}.\n\n"
            "Your internet connection may be unstable or something unexpected "
            "has gone wrong. "
            "Please consider logging out and restarting your client.",
            info=errmsg,
        ).exec()
        return

    def updatePreviewImage(self, new, old):
        """Updates the displayed image when the selection changes.

        Args:
            new (QItemSelection): the newly selected cells.
            old (QItemSelection): the previously selected cells.

        Returns:
            None
        """
        idx = new.indexes()
        if len(idx) == 0:
            # Remove preview when user unselects row (e.g., ctrl-click)
            log.debug("User managed to unselect current row")
            self.testImg.updateImage(None)
            return
        # Note: a single selection should have length 11 all with same row: could assert
        self._updateImage(idx[0].row())

    def ensureAllDownloaded(self, new, old):
        """Whenever the selection changes, ensure downloaders are either finished or running for each image.

        We might need to restart downloaders if they have repeatedly failed.
        Even if we are still waiting, we can signal to the download the we
        have renewed interest in this particular download.
        TODO: for example. maybe we should send a higher priority?  No: currently
        this also happens "in the background" b/c Marker selects the new row.

        Args:
            new (QItemSelection): the newly selected cells.
            old (QItemSelection): the previously selected cells.

        Returns:
            None
        """
        idx = new.indexes()
        if len(idx) == 0:
            return
        # Note: a single selection should have length 11 all with same row: could assert
        pr = idx[0].row()
        task = self.prxM.getPrefix(pr)
        src_img_data = self.examModel.get_source_image_data(task)
        self.get_downloads_for_src_img_data(src_img_data)

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

    def closeEvent(self, event: None | QtGui.QCloseEvent) -> None:
        log.debug("Something has triggered a shutdown event")
        while not self.Qapp.downloader.stop(500):
            if (
                SimpleQuestion(
                    self,
                    "Download threads are still in progress.",
                    question="Do you want to wait a little longer?",
                ).exec()
                == QMessageBox.StandardButton.No
            ):
                # TODO: do we have a force quit?
                break
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
            msg.setStandardButtons(
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
            button = msg.button(QMessageBox.StandardButton.Cancel)
            assert button
            button.setText("Wait (cancel close)")
            msg.setIcon(QMessageBox.Icon.Warning)
            if msg.exec() == QMessageBox.StandardButton.Cancel:
                if event:
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
        # after revoking, Downloader's msgr will be invalid
        self.Qapp.downloader.detach_messenger()
        try:
            self.msgr.closeUser()
        except PlomAuthenticationException:
            log.warning("User tried to logout but was already logged out.")
            pass
        log.debug("Emitting Marker shutdown signal")
        self.my_shutdown_signal.emit(
            2,
            [
                self.annotatorSettings["keybinding_name"],
                self.annotatorSettings["keybinding_custom_overlay"],
            ],
        )
        if event:
            event.accept()
        log.debug("Marker: goodbye!")

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
        pd.setWindowModality(Qt.WindowModality.WindowModal)
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
        """Run LaTeX on a fragment of text and return the file name of a PNG.

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
            cache_invalid_tryagain (bool): if True then when we get
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
                    info = '<font size="-3"><pre style="white-space: pre-wrap;">\n'
                    info += "\n".join(lines[max(0, n - 5) : n + 5])
                    info += "\n</pre></font>"
                    # TODO: Issue #2146, parent=self will cause Marker to popup on top of Annotator
                    InfoMsg(
                        None,
                        """
                        <p>The server was unable to process your TeX fragment.</p>
                        <p>Partial error message:</p>
                        """,
                        details=fragment,
                        info=info,
                        info_pre=False,
                    ).exec()
                else:
                    InfoMsg(
                        None,
                        "<p>The server was unable to process your TeX fragment.</p>",
                        details=fragment,
                    ).exec()
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

    def get_current_task_id_or_none(self) -> str | None:
        """Give back the task id string of the currently highlighted row or None."""
        prIndex = self.ui.tableView.selectedIndexes()
        if len(prIndex) == 0:
            return None
        # Note: a single selection should have length 11 (see ExamModel): could assert
        pr = prIndex[0].row()
        task_id_str = self.prxM.getPrefix(pr)
        return task_id_str

    def manage_tags(self):
        """Manage the tags of the current task."""
        task = self.get_current_task_id_or_none()
        if not task:
            return
        self.manage_task_tags(task)

    def manage_task_tags(self, task, parent=None):
        """Manage the tags of a task.

        Args:
            task (str): A string like "q0003g2" for paper 3 question 2.

        Keyword Args:
            parent (Window/None): Which window should be dialog's parent?
                If None, then use `self` (which is Marker) but if other
                windows (such as Annotator or PageRearranger) are calling
                this and if so they should pass themselves: that way they
                would be the visual parents of this dialog.

        Returns:
            None
        """
        if not parent:
            parent = self

        all_tags = [tag for key, tag in self.msgr.get_all_tags()]
        try:
            current_tags = self.msgr.get_tags(task)
        except PlomNoPaper as e:
            WarnMsg(parent, f"Could not get tags from {task}", info=str(e)).exec()
            return

        tag_choices = [X for X in all_tags if X not in current_tags]

        artd = AddRemoveTagDialog(parent, current_tags, tag_choices, label=task)
        if artd.exec() == QDialog.DialogCode.Accepted:
            cmd, new_tag = artd.return_values
            if cmd == "add":
                if new_tag:
                    try:
                        self.msgr.add_single_tag(task, new_tag)
                        log.debug('tagging paper "%s" with "%s"', task, new_tag)
                    except PlomBadTagError as e:
                        errmsg = html.escape(str(e))
                        WarnMsg(parent, "Tag not acceptable", info=errmsg).exec()
            elif cmd == "remove":
                try:
                    self.msgr.remove_single_tag(task, new_tag)
                except PlomConflict as e:
                    InfoMsg(
                        parent,
                        "Tag was not present, perhaps someone else removed it?",
                        info=html.escape(str(e)),
                    ).exec()
            else:
                # do nothing - but shouldn't arrive here.
                pass

            # refresh the tags
            try:
                current_tags = self.msgr.get_tags(task)
            except PlomNoPaper as e:
                WarnMsg(parent, f"Could not get tags from {task}", info=str(e)).exec()
                return

            try:
                self.examModel.setTagsByTask(task, current_tags)
                self.ui.tableView.resizeColumnsToContents()
                self.ui.tableView.resizeRowsToContents()
            except ValueError:
                # we might not own the task for which we've have been managing tags
                pass

    def setFilter(self):
        """Sets a filter tag."""
        search_terms = self.ui.filterLE.text().strip()
        if self.ui.filterInvCB.isChecked():
            self.prxM.set_filter_tags(search_terms, invert=True)
        else:
            self.prxM.set_filter_tags(search_terms)

    def _show_only_my_tasks(self) -> None:
        self.prxM.set_show_only_this_user(self.msgr.username)

    def _show_all_tasks(self) -> None:
        self.prxM.set_show_only_this_user("")

    def choose_and_view_other(self) -> None:
        """Ask user to choose a paper number and question, then show images."""
        max_question_idx = self.exam_spec["numberOfQuestions"]
        qlabels = [
            get_question_label(self.exam_spec, i + 1)
            for i in range(0, max_question_idx)
        ]
        tgs = SelectPaperQuestion(
            self,
            qlabels,
            max_papernum=self.max_papernum,
            initial_idx=self.question_idx,
        )
        if tgs.exec() != QDialog.DialogCode.Accepted:
            return
        paper_number, question_idx, get_annotated = tgs.get_results()
        self.view_other(
            paper_number, question_idx, _parent=self, get_annotated=get_annotated
        )

    def view_other(
        self,
        paper_number: int,
        question_idx: int,
        *,
        _parent: QWidget | None = None,
        get_annotated: bool = True,
    ) -> None:
        """Shows a particular paper number and question.

        Args:
            paper_number: the paper number to be viewed.
            question_idx: which question to be viewed.

        Keyword Args:
            get_annotated: whether to try to get the latest annotated
                image before falling back on the original scanned images.
                True by default.

        Returns:
            None
        """
        tn = paper_number
        q = question_idx

        stuff = None

        if _parent is None:
            _parent = self

        if get_annotated:
            try:
                annot_img_info, annot_img_bytes = self.msgr.get_annotations_image(tn, q)
            except PlomNoPaper:
                pass
            except PlomBenignException as e:
                s = f"Could not get annotation image: {e}"
                s += "\nWill try to get the original images next..."
                WarnMsg(self, s).exec()
            else:
                # TODO: nonunique if we ask again: no caching here
                im_type = annot_img_info["extension"]
                aname = self.workingDirectory / f"annot_{tn}_{q}.{im_type}"
                with open(aname, "wb") as fh:
                    fh.write(annot_img_bytes)
                stuff = [aname]
                s = f"Annotations for paper {tn:04} question index {q}"

        if stuff is None:
            try:
                # TODO: later we might be able to cache here
                # ("q" might not be our question number)
                pagedata = self.get_src_img_data(
                    paper_question_index_to_task_id_str(tn, q)
                )
            except PlomBenignException as e:
                WarnMsg(self, f"Could not get page data: {e}").exec()
                return
            if not pagedata:
                WarnMsg(
                    self,
                    f"No page images for paper {tn:04} question index {q}:"
                    " perhaps it was not written, not yet scanned,"
                    " or possibly that question is not yet scanned"
                    " or has been discarded.",
                ).exec()
                return
            # (even if pagedata not cached, the images will be here)
            pagedata = self.downloader.sync_downloads(pagedata)
            stuff = pagedata
            s = f"Original ungraded images for paper {tn:04} question index {q}"

        # TODO: Restore appending version to the title by fixing Issue #2695
        # qvmap = self.msgr.getQuestionVersionMap(tn)
        # ver = qvmap[q]
        # s += f" (ver {ver})"

        d = QuestionViewDialog(_parent, stuff, tn, q, marker=self, title=s)
        # TODO: future-proofing this a bit for live download updates
        # PC.download_finished.connect(d.shake_things_up)
        d.exec()
        d.deleteLater()  # disconnects slots and signals

    def get_file_for_previous_viewer(self, task):
        """Get the annotation file for the given task.

        Check to see if the
        local system already has the files for that task and if not grab them
        from the server. Then pass the annotation-image-file back to the
        caller.
        """
        # this checks to see if (all) the files for that task have
        # been downloaded locally already. If already present it
        # returns true, and if not then it grabs them from the server
        # and returns true. A 'false' is returned only when the
        # get-from-server fails.
        if not self.get_files_for_previously_annotated(task):
            return None
        # now grab the actual annotated-image filename
        return self.examModel.getAnnotatedFileByTask(task)
