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
from plom.plom_exceptions import PlomException
from .pagecache import PageCache


log = logging.getLogger("Downloader")


class Downloader(QObject):
    """Downloads images.

    TODO:
    - need to shut this down before we logout
    """

    # emitted anytime a (background) download finishes
    download_finished = pyqtSignal(int, str, str)
    # emitted anytime a (background) download fails
    # TODO: document whether it is automatically restarted?
    download_failed = pyqtSignal(int)

    def __init__(self, basedir, *, msgr=None):
        """Initialize a new Downloader.

        args:
            msgr (Messenger):
                Note Messenger is not multithreaded and blocks using
                mutexes.  Here we make our own private clone so caller
                can keep using their's.

        Downloader maintains a queue of downloads and emits signals
        whenever downloads succeed or fail.

        One enqueued a download will be automatically retried several
        times, but to prevent endless data usage, it will give up after
        three tries.  That is, clients cannot assume that something
        enqueued will inevitably be downloaded.  Clients can check by
        TODO: document how to check if something is in the queue or/and
        or currently downloading.

        TODO: document how to query the queue size, etc.

        TODO: how do we shutdown cleanly?  Currently if you logout
        another msgr while this is downloading, we'll get a crash...
        """
        super().__init__()
        # self.is_download_in_progress = False
        if msgr:
            self.msgr = Messenger.clone(msgr)
        else:
            self.msgr = None
        self.basedir = Path(basedir)
        self.write_lock = threading.Lock()
        self.pagecache = PageCache(basedir)
        # TODO: may want this in the QApp: only have one
        # TODO: just use QThreadPool.globalInstance()?
        self.threadpool = QThreadPool()
        self._tries = {}
        self._total_tries = {}

    def temp_attach_messenger(self, msgr):
        self.msgr = Messenger.clone(msgr)

    @classmethod
    def get_placeholder_path(cls):
        """A static image that can be used as a placeholder while images are downloading.

        Currently this must be a string (not an Path for example) b/c of some Qt
        limitations in the ExamModel and proxy stuff in Marker.

        TODO: a better image or perhaps an animation?
        """
        # Not imported earlier b/c of some circular import stuff (?)
        import plom.client.icons

        return str(resources.path(plom.client.icons, "manager_unknown.svg"))

    def download_in_background_thread(self, row, priority=False, _is_retry=False):
        """Enqueue the downloading of particular row of the image database.

        Args:
            row (dict): TODO

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
            self.threadpool.start(worker, priority=QThread.Priority.HighPriority)
        else:
            self.threadpool.start(worker, priority=QThread.Priority.LowPriority)
        # bg.finished.connect(thread.quit)
        # bg.finished.connect(bg.deleteLater)

        # keep track of retries
        x = self._tries.get(row["id"], 0)
        y = self._total_tries.get(row["id"], 0)
        self._tries[row["id"]] = x + 1 if _is_retry else 1
        self._total_tries[row["id"]] = y + 1

    def worker_delivers(self, img_id, md5, tmpfile, local_filename):
        log.debug(f"Worker delivery: {img_id}, {local_filename}")
        # TODO: maybe pagecache should have the desired filename?
        # TODO: and keep a list of downloads in-progress
        # TODO: revisit once PageCache decides None/Exception...
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
                # TODO emit or not?
                return
            raise RuntimeError(
                f"downloaded wrong thing? {cur}, {local_filename}, {md5}"
            )
        # Path(tmpfile).rename(target_name)
        Path(local_filename).parent.mkdir(exist_ok=True, parents=True)
        with self.write_lock:
            Path(tmpfile).rename(local_filename)
            self.pagecache.set_page_image_path(img_id, local_filename)
        self.download_finished.emit(img_id, md5, local_filename)

    def worker_failed(self, img_id, md5, local_filename, err_stuff_tuple):
        log.warning("Worker failed: %d, %s", img_id, str(err_stuff_tuple))
        self.download_failed.emit(img_id)
        x = self._tries[img_id]
        if x > 3:
            log.warning("We've tried %d too many times: giving up!", img_id)
            return
        # TODO: does not respect the original priority: high priority failure becomes ordinary
        self.download_in_background_thread(
            {"id": img_id, "md5": md5, "local_filename": local_filename},
            _is_retry=True,
        )

    def sync_downloads(self, pagedata):
        for row in pagedata:
            row = self.sync_download(row)
        return pagedata

    def sync_download(self, row):
        """Give the pagedata in row, download, cache and return edited row.

        Args:
            row (dict): one row of the metadata for the set of all pages
                involved in a question.  A list of dicts where each dict must
                have (at least) keys  ``id``, ``md5``, ``server_path``.
                TODO: cleanup docs.

        If the file is already downloaded, put its name into "local_filename"
        in ``row``.
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

    def download_page_images(self, pagedata, *, alt_get=None, get_all=False):
        """Download and cache images

        TODO: make it idempotent
        TODO: make it robust-ish if someone deletes files under us

        Returns:
            list: updated list of pagedata input (which was also changed: no
            copy is made).
        """
        for r in pagedata:
            r = self.sync_download(r)
        return pagedata


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        TODO: tuple (exctype, value, traceback.format_exc() )

    heres_the_goods
        int, str, str, str: id, TODO
    """

    finished = pyqtSignal()
    # error = pyqtSignal(tuple)
    # result = pyqtSignal(object)
    download_succeed = pyqtSignal(int, str, str, str)
    download_fail = pyqtSignal(int, str, str, tuple)


class DownloadWorker(QRunnable):
    def __init__(self, msgr, img_id, md5, target_name, *, basedir):
        super().__init__()
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
            fail = random.random() < 0.9
            debug_wait2 = random.randint(1, 2)
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
