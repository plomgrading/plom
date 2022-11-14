# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""
Tools for managing the local page cache.
"""

from copy import deepcopy
import logging
from pathlib import Path


log = logging.getLogger("PageCache")


class PageCache:
    """Manage a local on-disc cache of page images.

    TODO: record the time of caching
    """


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
        list: a modified copy of the input pagedata.
    """
    basedir = Path(basedir)
    pagedata = deepcopy(pagedata)
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
>>>>>>> origin/dev

    def __init__(self, basedir):
        super().__init__()
        self._image_paths = {}
        # self._image_md5 = {}
        self.basedir = Path(basedir)

    def has_page_image(self, img_id):
        r = self._image_paths.get(img_id, None)
        return r is not None

    def page_image_path(self, img_id):
        """

        TODO: document what happens if it doesn't exist?  Exception or None?
        """
        print(self._image_paths)
        return self._image_paths[img_id]

    def set_page_image_path(self, img_id, f):
        """TODO"""
        self._image_paths[img_id] = f

    def update_from_someone_elses_downloads(self, pagedata):
        # hopefully temporary!
        # TODO: maybe check the md5sums since we didn't get it ourselves
        for r in pagedata:
            if r["local_filename"]:
                cur = self._image_paths.get(r["id"], None)
                if cur is not None:
                    assert cur == r["local_filename"]
                else:
                    self._image_paths[r["id"]] = r["local_filename"]
