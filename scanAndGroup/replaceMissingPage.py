#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import fitz
import json
import os
import shutil
import sys
import tempfile

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


# load in the list of produced pages to check the version number.
def readExamsProduced():
    """Read the exams that were produced during build"""
    global examsProduced
    with open("../resources/examsProduced.json") as data_file:
        examsProduced = json.load(data_file)


# load in the list of scanned pages to check if the current page is already there.
def readExamsScanned():
    """Read the test/page we have scanned in 03/04 scripts"""
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open("../resources/examsScanned.json") as data_file:
            examsScanned = json.load(data_file)


# write the updated list of scanned papers
def writeExamsScanned():
    """Update the list of test/page/versions that have been scanned"""
    es = open("../resources/examsScanned.json", "w")
    es.write(json.dumps(examsScanned, indent=2, sort_keys=True))
    es.close()


# If all is good then build a substitute page and save it in the correct place
def buildSubstitute(test, page):
    tpImage = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    # create the test/page stamp using imagemagick
    os.system(
        "convert -pointsize 36 -size 200x42 caption:'{}.{}' -trim "
        "-gravity Center -extent 200x42 -bordercolor black "
        "-border 1 {}".format(str(test).zfill(4), str(page).zfill(2), tpImage.name)
    )

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
    os.system("convert -density 200 pns.pdf pns.png")
    os.unlink("pns.pdf")


def moveSubstitute(stest, spage, version):
    shutil.move(
        "pns.png",
        "decodedPages/page_{}/version_{}/t{}p{}v{}.png".format(
            spage.zfill(2), version, stest.zfill(4), spage.zfill(2), version
        ),
    )
    examsScanned[stest][spage] = [version, "pns.png"]

def print_usage():
    print(main.__doc__)

def main():
    """Replace missing (not scanned) pages with placeholders.

    Call this like:
    ./replaceMissingPage.py t p

    where `t` is the test number and `p` is the page number

    This is dangerous stuff: we do some sanity checks but be careful!
    """
    if len(sys.argv) != 3:
        print_usage()
        sys.exit(1)
    stest = sys.argv[1]
    spage = sys.argv[2]
    test = int(stest)
    page = int(spage)


    spec = TestSpecification()
    spec.readSpec()
    readExamsProduced()
    readExamsScanned()

    if test < 1 or test > spec.Tests:
        print("Test {} out of valid range".format(test))
        sys.exit(2)

    if page < 1 or page > spec.Length:
        print("Page {} out of valid range".format(page))
        sys.exit(3)

    # get the version of the test/page from the examsProduced list
    version = int(examsProduced[stest][spage])

    print("Looking for test {} page {} version {}".format(test, page, version))
    if stest not in examsScanned:
        print("Have not scanned any pages from test {}".format(test))
        print("Quitting")
        sys.exit(4)

    if spage in examsScanned[stest]:
        res = examsScanned[stest][spage]
        print(
            "Already scanned page {} from test {} as pageImage file {}".format(
                page, test, res[1]
            )
        )
        print("Quitting")
        sys.exit(5)

    print("Building substitute page")
    buildSubstitute(test, page)
    print("Copying substitute page into place")
    moveSubstitute(stest, spage, version)
    print("Updated examsScanned list")
    writeExamsScanned()


if __name__ == "__main__":
    main()
