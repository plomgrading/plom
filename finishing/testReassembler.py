#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import fitz
import os
import sys
import tempfile
import subprocess

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import __version__

# hardcoded for letter, https://gitlab.math.ubc.ca/andrewr/MLP/issues/276
papersize_portrait = (612, 792)
papersize_landscape = (792, 612)
margin = 10


def iswider(f):
    """True if image is wider than it is high"""
    # TODO: shell likely SLOW for this task...?
    ratio = (
        subprocess.check_output(["identify", "-format", "%[fx:w/h]", f])
        .decode()
        .rstrip()
    )
    return float(ratio) > 1


if __name__ == "__main__":
    shortName = sys.argv[1]
    sid = sys.argv[2]
    outdir = sys.argv[3]
    coverfname = sys.argv[4]
    # the groupimage files
    imgl = eval(sys.argv[5])

    # note we know the shortname is alphanumeric with no strings
    # so this is safe.
    outname = os.path.join(outdir, "{}_{}.pdf".format(shortName, sid))
    # TODO: check if anything changed (either here or in 09/08)
    # https://gitlab.math.ubc.ca/andrewr/MLP/issues/392
    if os.path.isfile(outname):
        exit(0)

    exam = fitz.open()
    if coverfname:
        exam.insertPDF(fitz.open(coverfname))

    for img in imgl:
        # Rotate page not the image: we want landscape on screen
        if iswider(img):
            w, h = papersize_landscape
        else:
            w, h = papersize_portrait
        pg = exam.newPage(width=w, height=h)
        rec = [margin, margin, w - margin, h - margin]
        pg.insertImage(rec, filename=img)

    exam.setMetadata(
        {
            "title": "{} {}".format(shortName, sid),
            "producer": "Plom {}".format(__version__),
        }
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        exam.save(outname)
