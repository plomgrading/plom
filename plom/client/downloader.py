# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

"""
The background downloader downloads images using threads.
"""

import logging
import random
import importlib.resources as resources
import tempfile
import threading
from time import sleep, time
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtCore import QThreadPool, QRunnable

from plom.messenger import Messenger
from plom.webPlomMessenger import WebPlomMessenger
from plom.plom_exceptions import PlomException
from .pagecache import PageCache


log = logging.getLogger("Downloader")


class Downloader(QObject):
    """Downloads and maintains a cache of images.

    TODO:
    - need to shut this down before we logout
    """

    # emitted anytime a (background) download finishes
    download_finished = pyqtSignal(int, str, str)
    # emitted anytime a (background) download fails
    # TODO: document whether it is automatically restarted?
    download_failed = pyqtSignal(int)
    # emitted when queue lengths change (i.e., things enqueued)
    download_queue_changed = pyqtSignal(dict)

    def __init__(self, basedir, *, msgr=None):
        """Initialize a new Downloader.

        args:
            msgr (Messenger):
                Note Messenger is not multithreaded and blocks using
                mutexes.  Here we make our own private clone so caller
                can keep using their's.

        Downloader maintains a queue of downloads and emits signals
        whenever downloads succeed or fail.

        Once enqueued, a download will be automatically retried several
        times, but to prevent endless data usage, it will give up after
        three tries.  That is, clients cannot assume that something
        enqueued will inevitably be downloaded.  Clients can check by
        TODO: document how to check if something is in the queue or/and
        or currently downloading.

        TODO: document how to query the queue size, etc.

        TODO: how do we shutdown cleanly?  Currently if you logout
        another msgr while this is downloading, we'll get a crash...

        The Downloader will emit various **signals**.  You can connect
        slots to these:

          * `download_finished(int, str, str)`: emitted when a
            (background) download finishes.
          * `download_failed(img_id: int)`: emitted when a (background)
            download fails.
          * `download_queue_changed(dict)`: the queue length changed
            (e.g., something enqueued or the queue is cleared).  The
            signal argument is a dict of information about the queue.
        """
        super().__init__()
        # self.is_download_in_progress = False
        if msgr:
            if type(msgr) == WebPlomMessenger:
                self.msgr = WebPlomMessenger.clone(msgr)
            else:
                self.msgr = Messenger.clone(msgr)
        else:
            self.msgr = None
        self.basedir = Path(basedir)
        self.write_lock = threading.Lock()
        self.pagecache = PageCache(basedir)
        # TODO: may want this in the QApp: only have one
        # TODO: just use QThreadPool.globalInstance()?
        self.threadpool = QThreadPool()
        # TODO: will this stop Marker from getting one?  It doesn't seem to...
        self.threadpool.setMaxThreadCount(2)
        self._tries = {}
        self._total_tries = {}
        self._in_progress = {}
        # it still counts as a fail if it eventually retried successfully
        self.number_of_fails = 0
        self._stopping = False

    def _attach_messenger(self, msgr):
        """Add/replace the current messenger."""
        if type(msgr) == WebPlomMessenger:
            self.msgr = WebPlomMessenger.clone(msgr)
        else:
            self.msgr = Messenger.clone(msgr)

    def _detach_messenger(self):
        """Stop our messenger and forget it (but do not logout)."""
        if self.msgr:
            self.msgr.stop()
        self.msgr = None

    def _has_messenger(self):
        """Do we have a messenger?"""
        if self.msgr:
            return True
        return False

    @classmethod
    def get_placeholder_path(cls):
        """A static image that can be used as a placeholder while images are downloading.

        Currently this must be a string (not an Path for example) b/c of some Qt
        limitations in the ExamModel and proxy stuff in Marker.

        TODO: Issue #2357: better image or perhaps an animation?
        """
        # Not imported earlier b/c of some circular import stuff (?)
        import plom.client.icons

        return str(resources.path(plom.client.icons, "manager_unknown.svg"))

    def get_stats(self):
        # TODO: would be nice to know the "gave up after 3 tries" failures...
        # TODO: track retries and fails (more positive!)
        in_progress_ids = [k for k, v in self._in_progress.items() if v is True]
        return {
            "cache_size": self.pagecache.how_many_cached(),
            "fail": self.number_of_fails,
            "queued": len(in_progress_ids),
            "in_progress_ids": in_progress_ids,
        }

    def print_queue(self):
        print("enumerating all jobs to check for in progress...")
        for k, v in self._in_progress.items():
            print((k, v))

    def clear_queue(self):
        """Cancel any enqueued (but not yet started) downloads.

        TODO: should this prevent further retries?
        """
        # self.threadpool.cancel()
        self.threadpool.clear()
        # print(f"children: {self.threadpool.children()}")
        # print("forcing in_progress to false...")
        for k, v in self._in_progress.items():
            self._in_progress[k] = False
        self.download_queue_changed.emit(self.get_stats())

    def stop(self, timeout=-1):
        """Try to stop the downloader, after waiting for threads to clear.

        Args:
            timeout (int): milliseconds seconds to wait before giving
                up.  ``-1`` to wait forever.

        Returns:
            bool: True if all threads finished or False if timeout reached.
        """
        self._stopping = True
        # first we clear the ones that haven't started
        self.clear_queue()
        # then wait for timeout for the in-progress ones
        return self.threadpool.waitForDone(timeout)

    def download_in_background_thread(self, row, priority=False, _is_retry=False):
        """Enqueue the downloading of particular row of the image database.

        Args:
            row (dict): One image entry in the "page data", has fields
                `id`, `md5` and some others that are used to try to
                choose a reasonable local file name.

        Keyword Args:
            priority (bool): high priority if user requested this (not a
                background download.
            _is_retry (bool): default False.  If True, this signifies an
                automatic retry.  Clients should probably not touch this.

        Does not start a new download if the Page Cache already has that image.
        It also tries to avoid enquing another request for the same image.
        """
        log.debug(
            "activeThreadCount = %d, maxThreadCount = %d",
            self.threadpool.maxThreadCount(),
            self.threadpool.activeThreadCount(),
        )

        if self.pagecache.has_page_image(row["id"]):
            return
        if not _is_retry and self._in_progress.get(row["id"]):
            # return early if this image id is already in queue
            # TODO but we should reset retries?
            return
        # try some things to get a reasonable local filename
        target_name = row.get("server_path", None)
        if target_name is None:
            target_name = row.get("local_filename", None)
        if target_name is None:
            target_name = row.get("filename", None)
        if target_name is None:
            raise NotImplementedError("TODO: then use a random value")
        target_name = self.basedir / target_name

        worker = DownloadWorker(
            self.msgr,
            row["id"],
            row["md5"],
            target_name,
            basedir=self.basedir,
        )
        worker.signals.download_succeed.connect(self.worker_delivers)
        worker.signals.download_fail.connect(self.worker_failed)
        if priority:
            self.threadpool.start(worker, priority=QThread.HighPriority)
        else:
            self.threadpool.start(worker, priority=QThread.LowPriority)
        # keep track of which img_ids are in progress
        # todo: semaphore around this and .start?
        self._in_progress[row["id"]] = True
        # bg.finished.connect(thread.quit)
        # bg.finished.connect(bg.deleteLater)

        # keep track of retries
        x = self._tries.get(row["id"], 0)
        y = self._total_tries.get(row["id"], 0)
        self._tries[row["id"]] = x + 1 if _is_retry else 1
        self._total_tries[row["id"]] = y + 1
        log.info(
            "image id %d: starting try %d (lifetime try %d)",
            row["id"],
            self._tries[row["id"]],
            self._total_tries[row["id"]],
        )
        # TODO: did it though?  Maybe more when it returns?
        self.download_queue_changed.emit(self.get_stats())

    def worker_delivers(self, img_id, md5, tmpfile, local_filename):
        """A worker has succeed and delivered a temp file to us.

        This will emit a signal that others can listen for.
        In some cases, the worker will deliver something that somone else
        has downloaded in the meantime.  In that case we do not emit a
        signal.
        """
        log.debug(f"Worker delivery: {img_id}, {local_filename}")
        # TODO: maybe pagecache should have the desired filename?
        # TODO: revisit once PageCache decides None/Exception...
        self._in_progress[img_id] = False
        if self.pagecache.has_page_image(img_id):
            cur = self.pagecache.page_image_path(img_id)
        else:
            cur = None
        if cur:
            if cur == local_filename:
                log.info(
                    "Someone else downloaded %d (%s) for us in the meantime, no action",
                    img_id,
                    local_filename,
                )
                # no emit in this case
                return
            raise RuntimeError(
                f"downloaded wrong thing? {cur}, {local_filename}, {md5}"
            )
        Path(local_filename).parent.mkdir(exist_ok=True, parents=True)
        with self.write_lock:
            Path(tmpfile).rename(local_filename)
            self.pagecache.set_page_image_path(img_id, local_filename)
        self.download_finished.emit(img_id, md5, local_filename)
        self.download_queue_changed.emit(self.get_stats())

    def worker_failed(self, img_id, md5, local_filename, err_stuff_tuple):
        """A worker has failed and called us: retry 3 times."""
        log.warning("Worker failed: %d, %s", img_id, str(err_stuff_tuple))
        self.number_of_fails += 1
        self.download_failed.emit(img_id)
        x = self._tries[img_id]
        if x >= 3:
            log.warning(
                "We've tried image %d too many times (try %d/3 and %d lifetime failures): giving up",
                img_id,
                self._tries[img_id],
                self._total_tries[img_id],
            )
            self._in_progress[img_id] = False
            return
        if self._stopping:
            log.warning("Not retrying image %d b/c we're stopping", img_id)
            self._in_progress[img_id] = False
            return
        # TODO: does not respect the original priority: high priority failure becomes ordinary
        self.download_in_background_thread(
            {"id": img_id, "md5": md5, "local_filename": local_filename},
            _is_retry=True,
        )
        self.download_queue_changed.emit(self.get_stats())

    def sync_downloads(self, pagedata):
        """Given a block of "pagedata" download all images synchronously and return updated data.

        Args:
            pagedata (list): a list of dicts, each dict described in
                `sync_download`.  Warning: we don't make a copy: it
                will be modified (and returned).

        Return:
            list: a list of dicts which consists of the updated input with
            filenames added/updated for each image.
        """
        for row in pagedata:
            row = self.sync_download(row)
        return pagedata

    def sync_download(self, row):
        """Given a row of "pagedata", download synchronously and return edited row.

        Args:
            row (dict): one row of the metadata for the set of all pages
                involved in a question.  A list of dicts where each dict must
                have (at least) keys  ``id``, ``md5``, ``server_path``.
                TODO: sometimes we seem to accept ``md5sum`` instead: should
                fix that.

        Return:
            dict: the modified row.  If the file was already downloaded, put
            its name into the ``local_filename`` key.  If we had to download
            it we also put the filename into ``local_filename``.
        """
        # TODO: revisit once PageCache decides None/Exception...
        if self.pagecache.has_page_image(row["id"]):
            cur = self.pagecache.page_image_path(row["id"])
            row_cur = row.get("local_filename", None)
            if row_cur is None:
                row["local_filename"] = cur
                # TODO: do we care if this matches row["server_path"]?
                return row
            assert (
                row_cur == cur
            ), f"row has a filename which does not match cache: {row_cur} vs {cur}"
            log.info("asked to download id=%d; already in cache", row["id"])
            return row
        f = self.basedir / row["server_path"]
        if f.exists():
            raise RuntimeError(
                f"asked to download {f}; unexpectedly we already have it"
            )
        log.info("downloading %s", f)
        # the server_path might have a few subdirs
        f.parent.mkdir(exist_ok=True, parents=True)
        # we're not entirely consistent...
        md5 = row.get("md5") or row["md5sum"]
        im_bytes = self.msgr.get_image(row["id"], md5)
        # im_type = imghdr.what(None, h=im_bytes)
        with open(f, "wb") as fh:
            fh.write(im_bytes)
        row["local_filename"] = str(f)
        self.pagecache.set_page_image_path(row["id"], row["local_filename"])
        return row


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread.

    Supported signals are:

    finished:
        No data

    download_success:
        `(img_id (int), md5 (str), tempfile (str), local_filename (str)`

    download_fail:
        `(img_id (int), md5 (str), local_filename (str), err_stuff_tuple (tuple)`
        where the tuple is `(exctype, value, traceback.format_exc()`.
    """

    finished = pyqtSignal()
    # error = pyqtSignal(tuple)
    # result = pyqtSignal(object)
    download_succeed = pyqtSignal(int, str, str, str)
    download_fail = pyqtSignal(int, str, str, tuple)


class DownloadWorker(QRunnable):
    def __init__(self, msgr, img_id, md5, target_name, *, basedir):
        super().__init__()
        if type(msgr) == WebPlomMessenger:
            self._msgr = WebPlomMessenger.clone(msgr)
        else:
            self._msgr = Messenger.clone(msgr)
        self.img_id = img_id
        self.md5 = md5
        self.target_name = Path(target_name)
        self.basedir = Path(basedir)
        self.signals = WorkerSignals()

    # https://www.pythonguis.com/tutorials/multithreading-pyqt-applications-qthreadpool/
    # consider try except with error signal

    @pyqtSlot()
    def run(self):
        debug = True
        if debug:
            fail = random.random() < 0.2
            debug_wait2 = random.randint(3, 8)
            debug_wait1 = random.random() * debug_wait2
            debug_wait2 -= debug_wait1
            sleep(debug_wait1)
        try:
            t0 = time()
            try:
                im_bytes = self._msgr.get_image(self.img_id, self.md5)
                if debug and fail:
                    # TODO: can get PlomNotAuthorized if the pre-clone msgr is logged out
                    raise NotImplementedError(
                        "TODO: what sort of exceptions are possible?"
                    )
            except PlomException as e:
                log.warning(f"vaguely expected failure! {str(e)}")
                self.signals.download_fail.emit(
                    self.img_id, self.md5, str(self.target_name), (str(e), "whut else?")
                )
                self.signals.finished.emit()
                return
            t1 = time()
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=self.basedir,
                prefix="downloading_",
                suffix=self.target_name.suffix,
                delete=False,
            ) as f:
                f.write(im_bytes)
            t2 = time()
        except Exception as e:
            # TODO: generic catch-all bad, beer good
            log.error(f"unexpected failure, wtf we do here?! {str(e)}")
            self.signals.download_fail.emit(
                self.img_id, self.md5, str(self.target_name), (str(e), "whut else?")
            )
            self.signals.finished.emit()
            return
        if debug:
            sleep(debug_wait2)
        if debug:
            log.debug(
                "worker time: %.3gs download, %.3gs write, %.3gs debuggery",
                t1 - t0,
                t2 - t1,
                debug_wait1 + debug_wait2,
            )
        else:
            log.debug("worker time: %.3gs download, %.3gs write", t1 - t0, t2 - t1)
        self.signals.download_succeed.emit(
            self.img_id, self.md5, f.name, str(self.target_name)
        )
        self.signals.finished.emit()
