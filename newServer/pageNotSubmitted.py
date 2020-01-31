#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import fitz
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile


# If all is good then build a substitute page and save it in the correct place
def buildSubstitute(test, page, ver):
    tpImage = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

    DNS = fitz.open(
        "../resources/pageNotSubmitted.pdf"
    )  # create a 'did not submit' pdf
    # create a box for the test number near top-centre
    # Get page width
    pW = DNS[0].bound().width
    rect = fitz.Rect(pW // 2 - 40, 20, pW // 2 + 40, 44)
    text = "{}.{}".format(str(test).zfill(4), str(page).zfill(2))
    rc = DNS[0].insertTextbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    DNS[0].drawRect(rect, color=[0, 0, 0])

    scale = 200 / 72
    img = DNS[0].getPixmap(alpha=False, matrix=fitz.Matrix(scale, scale))
    img.writePNG("pns.{}.{}.{}.png".format(test, page, ver))
    DNS.close()


def main():
    """Replace missing (not scanned) pages with placeholders.

    Call this like:
    ./replaceMissingPage.py t p

    where `t` is the test number and `p` is the page number

    This is dangerous stuff: we do some sanity checks but be careful!
    """
    stest = sys.argv[1]
    spage = sys.argv[2]
    sver = sys.argv[3]
    test = int(stest)
    page = int(spage)
    ver = int(sver)
    buildSubstitute(test, page, ver)


if __name__ == "__main__":
    main()
