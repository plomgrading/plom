# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""
Tools for managing the local page cache.
"""

import logging
from pathlib import Path

# import imghdr
# import tempfile
# import time


log = logging.getLogger("marker")


class PageCache:
    """Manage a local on-disc cache of page images."""

    def __init__(self, basedir, *, msgr=None):
        # TODO: a not-fully-thought-out datastore for immutable pagedata
        # Note: specific to this question: relax that!
        self._full_pagedata = {}
        self._image_paths = {}
        self._rows_by_id = {}
        self.basedir = basedir
        self.msgr = msgr

    def has_task_page_images(self, papernum, question):
        return True

    def has_page_image(self, img_id):
        r = self._image_paths.get(img_id, None)
        return r is not None

    def page_image_path(self, img_id):
        return self._image_paths[img_id]

    def _download_pages(self, pagedata, *, alt_get=None, get_all=False):
        """Temporary code?"""

        return download_pages(
            self.msgr, pagedata, self.basedir, alt_get=alt_get, get_all=get_all
        )

    def download_from_pagedata(
        self, papernum, question, pagedata, *, alt_get=None, get_all=False
    ):
        """TODO"""

        pagedata = self._download_pages(pagedata, alt_get=alt_get, get_all=get_all)
        self._full_pagedata[papernum] = pagedata
        for r in pagedata:
            if r["local_filename"]:
                assert (
                    self._image_paths.get(r["id"], None) is None
                ), "TODO, better error"
                self._image_paths[r["id"]] = r["local_filename"]
                self._rows_by_id[r["id"]] = r
        # TODO?
        return pagedata

    def messy_hacky_temp_update(self, papernum, pagedata):
        # TODO: roughly a copy of part of download_from_pagedata, w/o download
        self._full_pagedata[papernum] = pagedata
        for r in pagedata:
            if r["local_filename"]:
                cur = self._image_paths.get(r["id"], None)
                if cur is not None:
                    assert cur == r["local_filename"]
                else:
                    self._image_paths[r["id"]] = r["local_filename"]
                    # self._rows_by_id[r["id"]] = r

    def download_in_background_thread(self, img_id):
        raise NotImplementedError("lazy devs")

    def sync_download(self, img_id):
        pass


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
