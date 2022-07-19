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
from time import sleep
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtCore import QThreadPool, QRunnable

from plom.messenger import Messenger
from .pagecache import PageCache


log = logging.getLogger("Downloader")


class Downloader(QObject):
    """Downloads images.

    TODO:
    - need to shut this down before we logout
    """

    # emitted anytime a (background) download finiehes
    download_finished = pyqtSignal(int, str, str)
    # download_failed = pyqtSignal(int, str, str)

    def __init__(self, basedir, *, msgr=None):
        """Initialize a new Downloader.

        args:
            msgr (Messenger):
                Note Messenger is not multithreaded and blocks using
                mutexes.  Here we make our own private clone so caller
                can keep using their's.

        TODO: queue unused so far
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

    def download_in_background_thread(self, row, callback=None, priority=False):
        """

        Args:
            row (dict): TODO

        Keyword Args:
            priority (bool): high priority if user requested this (not a
                background download.

        Does not start a new download if the Page Cache already has that image.
        """
        print(f">>> maxThreadCount = {self.threadpool.maxThreadCount()}")
        print(f">>> activeThreadCount = {self.threadpool.activeThreadCount()}")

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
        worker.signals.heres_the_goods.connect(self.bg_delivers)
        if priority:
            self.threadpool.start(worker, priority=QThread.Priority.HighPriority)
        else:
            self.threadpool.start(worker, priority=QThread.Priority.LowPriority)
        # bg.finished.connect(thread.quit)
        # bg.finished.connect(bg.deleteLater)

    def bg_delivers(self, img_id, md5, tmpfile, local_filename):
        print(f">>> BG delivers: {img_id}, {local_filename}")
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

    def sync_downloads(self, pagedata):
        for row in pagedata:
            row = self.sync_download(row)
        return pagedata

    def sync_download(self, row):
        """Give the pagedata in row, download, cache and return edited row.

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
        im_bytes = self.msgr.get_image(row["id"], row["md5"])
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
    heres_the_goods = pyqtSignal(int, str, str, str)


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
            t = random.randint(0, 7)
            sleep(t)
        im_bytes = self._msgr.get_image(self.img_id, self.md5)
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=self.basedir,
            prefix="downloading_",
            suffix=self.target_name.suffix,
            delete=False,
        ) as f:
            f.write(im_bytes)
        if debug:
            sleep(8 - t)
        self.signals.heres_the_goods.emit(
            self.img_id, self.md5, f.name, str(self.target_name)
        )
        self.signals.finished.emit()


def download_pages(msgr, pagedata, basedir, *, alt_get=None, get_all=False):
    """Download all or some of the page images for a set of pagedata.

    Args:
        msgr: an open connected messenger.  TODO: decorator?
        pagedata (list): typically the metadata for the set of all pages
            involved in a paper.  A list of dicts where each dict must
            have (at least) keys  ``id``, ``md5``, ``server_path``
        basedir: paths relative to this.

    Keyword Args:
        get_all (bool): download all the images, ignoring the ``included``
            field of the ``pagedata``.  default: False.
        alt_get (None/list): aka ``src_img_data`` a subset of page images
            we must download.  Use this to override the ``included``
            field of the ``pagedata``.  It should also be a list of dicts
            where only the key ``id`` is used.  Has no effect if
            ``get_all=True`` is also passed.

    Return:
        list: the modified pagedata.  TODO: also modifies the
        original as a side effect.  Should we deepcopy it first?
    """
    basedir = Path(basedir)
    for row in pagedata:
        row["local_filename"] = None
        f = basedir / row["server_path"]
        # if cache_do_we_have(row["id"]):
        dl = False
        if f.exists():
            row["local_filename"] = str(f)
        elif get_all:
            dl = True
        elif alt_get:
            if row["id"] in [r["id"] for r in alt_get]:
                dl = True
        elif row["included"]:
            dl = True

        if dl:
            log.debug("PageCache: downloading %s", f)
            f.parent.mkdir(exist_ok=True, parents=True)
            im_bytes = msgr.get_image(row["id"], row["md5"])
            # im_type = imghdr.what(None, h=im_bytes)
            with open(f, "wb") as fh:
                fh.write(im_bytes)
            row["local_filename"] = str(f)
    return pagedata
