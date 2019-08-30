__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import sys
import os
import fitz
import tempfile

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification

# Take command line parameters
# 1 = test
# 2 = page

test = int(sys.argv[1])
page = int(sys.argv[2])


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


# If all is good then build a substitute page and save it in the correct place
def buildSubstitute():
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

    DNS.save("argh.pdf", garbage=4, deflate=True, clean=True)


spec = TestSpecification()
spec.readSpec()
readExamsProduced()
readExamsScanned()

if test < 1 or test > spec.Tests:
    print("Test {} out of valid range".format(test))
    exit()

if page < 1 or page > spec.Length:
    print("Page {} out of valid range".format(page))
    exit()

# get the version of the test/page from the examsProduced list
version = int(examsProduced[str(test)][str(page)])
