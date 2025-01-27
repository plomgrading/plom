# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Lior Silberman
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

import logging
import pathlib
import queue
import random
import threading
import time

from PyQt6.QtCore import (
    QThread,
    QTimer,
    pyqtSignal,
)

from plom.messenger import Messenger
from plom.plom_exceptions import (
    PlomConflict,
    PlomException,
    PlomQuotaLimitExceeded,
    PlomSeriousException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
)

log = logging.getLogger("marker")


class BackgroundUploader(QThread):
    """Uploads exams in Background."""

    uploadSuccess = pyqtSignal(str, dict)
    uploadFail = pyqtSignal(str, str, bool, bool)
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

        It will eventually try to upload.  It will either succeed or fail.
        Either way, signals will be omitted.  Users of this object will
        likely want to connect to those.  Notably on fail, there is is no
        automatic retry.  You'd need to re-queue it if you want that.  But
        be careful: uploads are quite expensive so we do not want endless
        retries without user in the loop.

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
                self.uploadFail.emit(code, "Simulated upload failure!", False, True)
                self.num_failed += 1
            else:
                if synchronous_upload(
                    self._msgr,
                    *data,
                    failCallback=self.uploadFail.emit,
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


def synchronous_upload(
    _msgr: Messenger,
    task: str,
    grade: float | int,
    aname: pathlib.Path,
    pname: pathlib.Path,
    marking_time: float | int,
    question_idx: int,
    ver: int,
    rubrics: list,
    integrity_check: str,
    failCallback=None,
    successCallback=None,
) -> bool:
    """Uploads a paper.

    Args:
        _msgr: the messenger object, hopefully connected and ready to upload.
        task: the Task ID for the page being uploaded. Takes the form
            "q1234g9" = test 1234 question 9.
        grade: grade given to question.
        aname: the annotated file.
        pname: the `.plom` file.
        marking_time: the marking time (s) for this specific question.
        question_idx: the question index number.
        ver: the version number.
        rubrics: list of rubrics used.
        integrity_check: the integrity_check string of the task.
        failCallback: call this function if we fail.
        successCallback: a function to call when we succeed.

    Returns:
        True for success, False for failure.

    Raises:
        PlomSeriousException: elements in filenames do not correspond to
            the same exam, which would indicate a programming error and
            should not happen.
    """
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
        progress_info = _msgr.MreturnMarkedTask(
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
        failCallback(task, str(ex), True, False)
        return False
    except PlomQuotaLimitExceeded as ex:
        failCallback(task, str(ex), False, False)
        return False
    except PlomException as ex:
        failCallback(task, str(ex), False, True)
        return False

    # TODO: easy enough to call _msgr.get_marking_progress here and thus
    # avoid special returns above, but what if 1st succeeds and 2nd fails?

    successCallback(task, progress_info)
    return True
