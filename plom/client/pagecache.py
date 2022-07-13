# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""
Tools for managing the local page cache.
"""

import logging
import random
import tempfile
import time
import threading
from pathlib import Path

# import imghdr


from PyQt5.QtCore import (
    QObject,
    QThread,
    pyqtSlot,
    pyqtSignal,
)

from plom.messenger import Messenger


log = logging.getLogger("PageCache")


class BackgroundImageDownloader(QObject):
    finished = pyqtSignal()
    # id, md5, local_filename, status (useless?)
    heres_the_goods = pyqtSignal(int, str, str, str)
    # TODO: failure

    def __init__(self, msgr, img_id, md5, target_name, *, basedir, lock):
        super().__init__()
        self._msgr = Messenger.clone(msgr)
        self.img_id = img_id
        self.md5 = md5
        self.target_name = Path(target_name)
        self.basedir = Path(basedir)
        self.lock = lock

    def run(self):
        im_bytes = self._msgr.get_image(self.img_id, self.md5)
        f = self.target_name
        with self.lock:
            if f.exists():
                # someone beat us to it!
                status = "lost_race"
            else:
                f.parent.mkdir(exist_ok=True, parents=True)
                with open(f, "wb") as fh:
                    fh.write(im_bytes)
                status = "we_won"
        time.sleep(3)
        self.heres_the_goods.emit(self.img_id, self.md5, str(self.target_name), status)
        self.finished.emit()


class PageCache(QObject):
    """Manage a local on-disc cache of page images.

    TODO: record the time of caching
    """

    # emitted anytime a (background) download finiehes
    a_download_finished = pyqtSignal(int, str, str)

    def __init__(self, basedir, *, msgr=None):
        super().__init__()
        self._image_paths = {}
        # self._image_md5 = {}
        self.basedir = Path(basedir)
        self.msgr = msgr
        self._threads = []
        self._bgs = []
        self.write_lock = threading.Lock()

    def has_page_image(self, img_id):
        r = self._image_paths.get(img_id, None)
        return r is not None

    def page_image_path(self, img_id):
        return self._image_paths[img_id]

    def download_page_images(self, pagedata, *, alt_get=None, get_all=False):
        """Download and cache images

        TODO: make it idempotent
        TODO: make it robust-ish if someone deletes files under us

        Returns:
            list: updated list of pagedata input (which was also changed: no
            copy is made).
        """
        # TODO: Consider rewriting to use self.sync_download directly?
        pagedata = download_pages(
            self.msgr, pagedata, self.basedir, alt_get=alt_get, get_all=get_all
        )
        for r in pagedata:
            # if r.get("local_filename", None):
            if r["local_filename"]:
                assert (
                    self._image_paths.get(r["id"], None) is None
                ), "TODO, better error"
                self._image_paths[r["id"]] = r["local_filename"]
            # r = self. sync_download(r)
        return pagedata

    def update_from_someone_elses_downloads(self, pagedata):
        # hopefully tempoary!
        # TODO: maybe check the md5sums since we didn't get it ourselves
        for r in pagedata:
            if r["local_filename"]:
                cur = self._image_paths.get(r["id"], None)
                if cur is not None:
                    assert cur == r["local_filename"]
                else:
                    self._image_paths[r["id"]] = r["local_filename"]

    def sync_download_missing_images(self, pagedata):
        for row in pagedata:
            row = self.sync_download(row)
        return pagedata

    def download_in_background_thread(self, row, callback=None):
        thread = QThread()
        target_name = self.basedir / row["server_path"]
        bg = BackgroundImageDownloader(
            self.msgr,
            row["id"],
            row["md5"],
            target_name,
            basedir=self.basedir,
            lock=self.write_lock,
        )
        bg.moveToThread(thread)
        thread.started.connect(bg.run)
        bg.finished.connect(thread.quit)
        bg.finished.connect(bg.deleteLater)
        bg.heres_the_goods.connect(self.bg_delivers)
        if callback:
            bg.heres_the_goods.connect(callback)

        thread.finished.connect(thread.deleteLater)
        # bg_bgimg.progress.connect(self.reportProgress)
        thread.start()
        # TODO: where to put it?  how to clean up?
        self._threads.append(thread)
        self._bgs.append(bg)

    def bg_delivers(self, img_id, md5, local_filename, status):
        print(f">>> BG delivers: {img_id}, {local_filename}")
        cur = self._image_paths.get(img_id, None)
        if cur:
            if cur == local_filename:
                assert status == "lost_race"
                log.info(
                    "Someone else downloaded %d (%s) for us in the meantime, no action",
                    img_id,
                    local_filename,
                )
                return
            raise RuntimeError(
                f"downloaded wrong thing? {cur}, {local_filename}, {md5}"
            )
        # Path(tmpfile).rename(target_name)
        self._image_paths[img_id] = local_filename
        self.a_download_finished.emit(img_id, md5, local_filename)

    # TODO: I think I'd prefer the PageCache is just a page cache and there is a separate
    # BGDownloader object, with a priority queue and a thread pool.  But can that background
    # downloader access the PageCache?

    def sync_download(self, row):
        """Give the pagedata in row, download, cache and return edited row."""

        row["local_filename"] = None
        f = self.basedir / row["server_path"]
        # if cache_do_we_have(row["id"]):
        cur = self._image_paths.get(row["id"], None)
        if f.exists():
            assert cur == str(f)
            log.info("asked to download %s; we already have it", f)
            row["local_filename"] = str(f)
            return row
        assert cur is None
        log.info("downloading %s", f)
        f.parent.mkdir(exist_ok=True, parents=True)
        im_bytes = self.msgr.get_image(row["id"], row["md5"])
        # im_type = imghdr.what(None, h=im_bytes)
        with open(f, "wb") as fh:
            fh.write(im_bytes)
        row["local_filename"] = str(f)
        self._image_paths[row["id"]] = row["local_filename"]
        return row


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
