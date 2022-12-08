# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""
Tools for managing the local page cache.
"""

import logging
from pathlib import Path


log = logging.getLogger("PageCache")


class PageCache:
    """Manage a local on-disc cache of page images.

    TODO: record the time of caching
    """

    def __init__(self, basedir):
        super().__init__()
        self._image_paths = {}
        # self._image_md5 = {}
        self.basedir = Path(basedir)

    def has_page_image(self, img_id):
        r = self._image_paths.get(img_id, None)
        return r is not None

    def how_many_cached(self):
        return len(self._image_paths)

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
            if r["filename"]:
                cur = self._image_paths.get(r["id"], None)
                if cur is not None:
                    assert cur == r["filename"]
                else:
                    self._image_paths[r["id"]] = r["filename"]
