#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

"""
Crawl a directory of zip files and upload contents to Plom.

Instructions: define PLOM_SERVER and PLOM_SCANNER_PASSWORD environment
variables.  Run this script in directory of zip files that come from
Canvas.

Needs access to a Canvas-exported classlist in order to map canvas user
id's onto student numbers.  See `df` below.

For each zip:
  * discard useless things like `__MACOSX` folders
  * upload jpg/jpeg/png files to the appropriate student number
  * warn on any PDF files and extract them for processing by
    `plom-hwscan` or `plom-scan`
  * move the zip file to a "done" folder.

Currently the bitmaps are treated as HW pages as we don't check for QR
codes but this could be changed.
"""

import os
import shutil
from pathlib import Path
import zipfile
import hashlib
import tempfile
from stdiomask import getpass

import pandas as pd

from plom.messenger import ScanMessenger
from plom.misc_utils import working_directory
from plom.scan.bundle_utils import bundle_name_and_md5_from_file


where_csv = Path("../../")
in_csv = where_csv / "classlist_section_sorted_noblank.csv"
df = pd.read_csv(in_csv)


def sid_name_from_cid(df, cid):
    """Get the name and Student ID associated with a Canvas User ID.

    TODO: for now, this needs the spreadsheet passed in."""
    L = df[df["ID"] == int(cid)].index.tolist()
    assert len(L) == 1
    (i,) = L
    name = df["Student"].iloc[i]
    sid = df["Student Number"].iloc[i]
    sid = int(sid)  # json grumpy about numpy.int64
    return (sid, name)


def cid_name_from_canvas_submitted_filename(f):
    """Extract the canvas user ID and part of name from a filename.

    The filename typically comes from Canvas which writes
    user-uploaded files with names like:
      - `lastfirst_LATE_123456_1234567_What They Called It.zip`
      - `lastfirst_123456_1234567_What They Called It.zip`

    Here we want the number "123456" called the Canvas User ID.

    Args:
        f (str/pathlib.Path): filename, possibly a path.

    Returns:
        tuple: `(name, cid)` for the name and Canvas User ID.
    """
    f = Path(f)
    L = f.stem.split("_")
    try:
        L.remove("LATE")
    except ValueError:
        pass
    if len(L) < 2 or not L[1].isdigit():
        raise ValueError('file "{}" not from Canvas?'.format(f))
    cid = L[1]
    assert cid.isdigit()
    # assert len(cid) == 6  # not always?
    name = L[0]
    assert name.isalnum()
    return (cid, name)


def get_and_start_scan_msgr(server=None, password=None):
    """Get a scanner messenger.

    Args:
        server (str): "server:port" or localhost default if omitted.
        password (str): prompts on the command line if omitted.

    Returns:
        ScanMessenger: authenticated connection to the server.  When you
            are done with this you should call `.closeUser()` and then
            `.stop()`.

    Raises:
        PlomExistingLoginException: scanner is logged in somewhere else.
            TODO: xref the force logout function once it exists.
            TODO: for now use command line tool `plom-scan clear`.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    if password is None:
        password = getpass("Please enter the 'scanner' password: ")

    msgr.requestAndSaveToken("scanner", password)
    return msgr


if __name__ == "__main__":
    q = [1, 2]
    print('TODO: Question hardcoded to "{}"'.format(q))

    try:
        server = os.environ["PLOM_SERVER"]
    except KeyError:
        server = None
    scan_pw = os.environ["PLOM_SCAN_PASSWORD"]
    msgr = get_and_start_scan_msgr(server=server, password=scan_pw)

    done = Path("done")
    os.makedirs(done, exist_ok=True)

    for f in Path(".").glob("*.zip"):
        print("=" * 80)
        print("=" * 80)
        print(f)
        cid, name_from_file = cid_name_from_canvas_submitted_filename(f)
        sid, name = sid_name_from_cid(df, cid)
        print("Canvas ID number: {}\tStudent ID: {}".format(cid, sid))
        if name[0].lower() not in name_from_file.lower():
            print(
                'sanity failure: name "{}" matches "{}"?'.format(name, name_from_file)
            )
            input("Press <enter> to continue or <ctrl>-c to stop ")

        # TODO: maybe can support bz2 gzip lzma too?
        assert zipfile.is_zipfile(f)
        with zipfile.ZipFile(f) as z:
            stuff = z.infolist()
            # stuff = z.namelist()
            # shovel up the mac droppings
            stuff = [x for x in stuff if "__macosx" not in x.filename.lower()]
            print("\n  ".join([str(x) for x in stuff]))
            bundle_name, md5 = bundle_name_and_md5_from_file(f)
            bundle_success = msgr.createNewBundle(bundle_name, md5)
            if not bundle_success[0]:
                print(bundle_success)
                raise RuntimeError("bundle making failed?")
            input("Press <enter> to continue or <ctrl>-c to stop ")
            # TODO: could refactor to use plom.scan.sendPagesToServer.upload_HW_pages
            for n, x in enumerate(stuff):
                print("-" * 80)
                if (
                    x.filename.lower().endswith(".jpg")
                    or x.filename.lower().endswith(".jpeg")
                    or x.filename.lower().endswith(".png")
                ):
                    print('we get got jpeg/png in "{}"'.format(x.filename))
                elif x.filename.lower().endswith(".pdf"):
                    print("*** Oh no, a pdf---please deal with this manually.")
                    print('we are extracting "{}" for you'.format(x))
                    z.extract(x)
                    input("skip and keep going? (enter or ctrl-c) ")
                    continue
                else:
                    print('zip contents "{}" are being skipped'.format(x.filename))
                    continue
                with z.open(x, "r") as thefile:
                    md5 = hashlib.md5(thefile.read()).hexdigest()
                    input("keep going?")
                d = tempfile.TemporaryDirectory()
                with working_directory(d):
                    print(d)
                    # TODO: use it in memory instead, as in the md5 calc above
                    # TODO: check for QRs?  we always use HW pages currently
                    z.extract(x)
                    args = (sid, q, n, x, md5, bundle_name, n)
                    print(f"debug: args for upload: {args}")
                    rmsg = msgr.uploadHWPage(*args)
                    if not rmsg[0]:
                        raise RuntimeError(
                            f"Unsuccessful HW upload, server returned:\n{rmsg[1:]}"
                        )
            updates = msgr.triggerUpdateAfterHWUpload()
            print(updates)
        shutil.move(f, done / f)
    msgr.closeUser()
    msgr.stop()
