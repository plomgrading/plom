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
    # create the test/page stamp using imagemagick
    cmd = shlex.split(
        "convert -pointsize 36 -size 200x42 caption:'{}.{}' -trim "
        "-gravity Center -extent 200x42 -bordercolor black "
        "-border 1 {}".format(str(test).zfill(4), str(page).zfill(2), tpImage.name)
    )
    subprocess.check_call(cmd)

    DNS = fitz.open(
        "../resources/pageNotSubmitted.pdf"
    )  # create a 'did not submit' pdf
    # create a box for the test number near top-centre
    # Get page width
    pW = DNS[0].bound().width
    rTC = fitz.Rect(pW // 2 - 50, 20, pW // 2 + 50, 40)
    testnumber = fitz.Pixmap(tpImage.name)
    DNS[0].insertImage(rTC, pixmap=testnumber, overlay=True, keep_proportion=False)

    DNS.save("pns.pdf", garbage=4, deflate=True, clean=True)
    cmd = shlex.split(
        "convert -background white -alpha remove -alpha off -density 200 pns.pdf pns.{}.{}.{}.png".format(
            test, page, ver
        )
    )
    subprocess.check_call(cmd)
    os.unlink("pns.pdf")


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
