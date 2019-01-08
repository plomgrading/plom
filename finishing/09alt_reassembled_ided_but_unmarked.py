__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "GPLv3"

from collections import defaultdict
import json
import os
import sys

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


def readExamsGrouped():
    """Read json of marked'd tests. Store in examsMarked.
    Indexed by [testnumber][pagegroup], stores mark and version number.
    """
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open("../resources/examsGrouped.json") as data_file:
            examsGrouped = json.load(data_file)


def readExamsIDed():
    """Read json of ID'd tests. Store in examsIDed.
    Stores the studentID and StudentName along with testnumber.
    """
    global examsIDed
    if os.path.exists("../resources/examsIdentified.json"):
        with open("../resources/examsIdentified.json") as data_file:
            examsIDed = json.load(data_file)


def imageList(n):
    """
    Creates a list of the image files to be reassembled into
    and identified (but not marked) paper.
    This will be passed to the reassembly script.
    """
    # list of image files for the reassembly
    imgl = []
    # zeroth is the ID-group
    imgl.append(
        "../scanAndGroup/readyForMarking/idgroup/{}.png".format(examsGrouped[n][0])
    )
    # then the grouped pages
    for pg in range(spec.getNumberOfGroups()):
        # note pg is offset by 1.
        # get the version as last digit of the tgv code:
        v = examsGrouped[n][pg + 1][1:][-1]
        # groupimage from the approrpiate subdirectory
        imgl.append(
            "../scanAndGroup/readyForMarking/group_{}/version_{}/{}.png".format(
                str(pg + 1).zfill(2), v, examsGrouped[n][pg + 1]
            )
        )
    return imgl


# read the test spec
spec = TestSpecification()
spec.readSpec()
# read the ID'd and grouped exams.
readExamsIDed()
readExamsGrouped()
# Open a file for the list of commands to process to reassemble papers
fh = open("./commandlist.txt", "w")
for n in sorted(examsIDed.keys()):
    fh.write(
        'python3 testReassembler_only_ided.py {} "{}"\n'.format(
            examsIDed[n][1], imageList(n)
        )
    )
fh.close()
# pipe the commandlist into gnu-parallel
os.system("parallel --bar <commandlist.txt")
# delete the commandlist file.
os.unlink("commandlist.txt")
