#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import fitz
import os
import sys
import tempfile
import subprocess

from plom import __version__

# hardcoded for letter, https://gitlab.math.ubc.ca/andrewr/MLP/issues/276
papersize_portrait = (612, 792)
papersize_landscape = (792, 612)
margin = 10


def is_wider(f_name):
    """True if image is wider than it is high.

    Args:
        f_name (str): The name of the file we are checking.

    Returns:
        boolean : True if the image is wider than it is tall, False otherwise.
    """
    # TODO: shell likely SLOW for this task...?
    ratio = (
        subprocess.check_output(["identify", "-format", "%[fx:w/h]", f_name])
        .decode()
        .rstrip()
    )
    return float(ratio) > 1


def reassemble(out_name, short_name, sid, cover_fname, img_list):
    """Reassemble a pdf from the cover and question images.

    Leave cover_fname as None to omit it (e.g., when totalling).

    Return True if successful or False if the pdf file already exists.
    Note: no attempt is made to check if its correct; merely that it
    exists.  TODO: check if anything changed here or later [1].

    [1] https://gitlab.math.ubc.ca/andrewr/MLP/issues/392

    Args:
        out_name (str): name of the file we are assembling.
        short_name (str): name of the file without the whole directory. 
        sid (str): the student id.
        cover_fname (str): the name of the file of the coverpage of this test.
        img_list (str): the groupimage files

    Returns:
        bool: [description]
    """

    if os.path.isfile(out_name):
        return False

    exam = fitz.open()
    if cover_fname:
        exam.insertPDF(fitz.open(cover_fname))

    for img in img_list:
        # Rotate page not the image: we want landscape on screen
        if is_wider(img):
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait
        pg = exam.newPage(width=w, height=h)
        rec = [margin, margin, w - margin, h - margin]
        pg.insertImage(rec, filename=img)

    exam.setMetadata(
        {
            "title": "{} {}".format(short_name, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        exam.save(out_name, deflate=True)


if __name__ == "__main__":
    short_name = sys.argv[1]
    sid = sys.argv[2]
    outdir = sys.argv[3]
    cover_fname = sys.argv[4]
    # the groupimage files
    imglist = eval(sys.argv[5])

    # note we know the shortname is alphanumeric with no strings
    # so this is safe.
    outname = os.path.join(outdir, "{}_{}.pdf".format(short_name, sid))
    reassemble(outname, short_name, sid, cover_fname, img_list)
