# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Colin B. Macdonald

"""Tools for managing the local page cache."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


log = logging.getLogger("PageCache")


class PageCache:
    """Manage a local on-disc cache of page images.

    TODO: record the time of caching
    """

    def __init__(self, basedir: str | Path):
        super().__init__()
        self._image_paths: dict[int, Path] = {}
        # self._image_md5 = {}
        self.basedir = Path(basedir)
        log.info("Starting a new pagecache: %s", self.basedir)

    def wipe_cache(self) -> None:
        img_ids = list(self._image_paths.keys())
        log.info("Erasing the pagecache of %d images: %s", len(img_ids), self.basedir)
        # carefully erase dict without iterating over it
        for img_id in img_ids:
            p = self._image_paths.pop(img_id)
            log.debug("Erasing image id %d: %s", img_id, p)
            p.unlink()

    def has_page_image(self, img_id: int) -> bool:
        r = self._image_paths.get(img_id, None)
        return r is not None

    def how_many_cached(self) -> int:
        return len(self._image_paths)

    def page_image_path(self, img_id: int) -> Path:
        # TODO: document what happens if it doesn't exist?  Exception or None?
        return self._image_paths[img_id]

    def set_page_image_path(self, img_id: int, f: str | Path) -> None:
        # TODO: require Path only?
        self._image_paths[img_id] = Path(f)

    def update_from_someone_elses_downloads(
        self, pagedata: list[dict[str, Any]]
    ) -> None:
        # hopefully temporary!
        # TODO: maybe check the md5sums since we didn't get it ourselves
        for r in pagedata:
            if r["filename"]:
                cur = self._image_paths.get(r["id"], None)
                if cur is not None:
                    assert cur == r["filename"]
                else:
                    self._image_paths[r["id"]] = r["filename"]
