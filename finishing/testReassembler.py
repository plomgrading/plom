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

# hardcoded for letter, https://gitlab.math.ubc.ca/andrewr/MLP/issues/276
sizeportrait = "612x792"
sizelandscape = "792x612"


def iswider(f):
    """True if image is wider than it is high"""
    ratio = subprocess.check_output(["identify", "-format",
                                     "%[fx:w/h]", f]).decode().rstrip()
    return float(ratio) > 1


if __name__ == '__main__':
    # takes StudentID and list of group image files as args.
    # 0th item on list is the coverpage.
    # other items are the groupimage files.
    sid = eval(sys.argv[1])
    imgl = eval(sys.argv[2])
    coverfname, imgl = imgl[0], imgl[1:]
    # output as test_<StudentID>.pdf
    outname = "reassembled/test_{}.pdf".format(sid)


    # use imagemagick to convert each group-image into a temporary pdf.
    pdfpages = [tempfile.NamedTemporaryFile(suffix=".pdf") for x in imgl]
    for img, TF in zip(imgl, pdfpages):
        cmd = ["convert", img, "-quality", "100"]
        # TODO: want to center the image but then it doesn't fit page
        #cmd += ["-gravity", "center", "-background", "white"]
        # Rotate page not the image: we want landscape on screen
        if iswider(img):
            cmd += ["-page", sizelandscape]
        else:
            cmd += ["-page", sizeportrait]
        cmd += ["pdf:{}".format(TF.name)]
        subprocess.check_call(cmd)

    # open the coverpage and append the temporary pdf pages
    exam = fitz.open(coverfname)
    for pg in pdfpages:
        exam.insertPDF(fitz.open(pg.name))

    # clean up temp files
    for pg in pdfpages:
        pg.close()

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        exam.save(outname)
