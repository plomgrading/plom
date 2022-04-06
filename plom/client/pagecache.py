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
