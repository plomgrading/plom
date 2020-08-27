#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import os
import sys
import tempfile
import subprocess

import fitz

from plom import __version__

# hardcoded for letter, https://gitlab.com/plom/plom/issues/276
papersize_portrait = (612, 792)
papersize_landscape = (792, 612)
margin = 10


def is_wider(f):
    """True if image is wider than it is high.

    Args:
        f (str): The name of the file we are checking.

    Returns:
        boolean : True if the image is wider than it is tall, False otherwise.
    """
    # TODO: shell likely SLOW for this task...?
    ratio = (
        subprocess.check_output(["identify", "-format", "%[fx:w/h]", f])
        .decode()
        .rstrip()
    )
    return float(ratio) > 1


def reassemble(outname, shortName, sid, coverfname, imglist):
    """Reassemble a pdf from the cover and question images.

    Leave coverfname as None to omit it (e.g., when totalling).

    Return True if successful or False if the pdf file already exists.
    Note: no attempt is made to check if its correct; merely that it
    exists.
    """
    if os.path.isfile(outname):
        return False

    exam = fitz.open()
    if coverfname:
        exam.insertPDF(fitz.open(coverfname))

    for img in imglist:
        # Rotate page not the image: we want landscape on screen
        if is_wider(img):
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait
        pg = exam.newPage(width=w, height=h)
        rec = fitz.Rect(margin, margin, w - margin, h - margin)
        pg.insertImage(rec, filename=img)

    exam.setMetadata(
        {
            "title": "{} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        exam.save(outname, deflate=True)


if __name__ == "__main__":
    shortName = sys.argv[1]
    sid = sys.argv[2]
    outdir = sys.argv[3]
    coverfname = sys.argv[4]
    # the groupimage files
    imglist = eval(sys.argv[5])

    # note we know the shortname is alphanumeric with no strings
    # so this is safe.
    outname = os.path.join(outdir, "{}_{}.pdf".format(shortName, sid))
    reassemble(outname, shortName, sid, coverfname, imglist)
