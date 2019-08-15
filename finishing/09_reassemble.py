__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

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


def readExamsCompleted():
    """Read json of completed (ie marked+id'd) tests.
    Store in examsCompleted
    """
    global examsCompleted
    if os.path.exists("../resources/examsCompleted.json"):
        with open("../resources/examsCompleted.json") as data_file:
            examsCompleted = json.load(data_file)


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
    a completed testpaper.
    This will be passed to the reassembly script.
    """
    imgl = []
    # the ID-group pages
    imgl.append(
        "../scanAndGroup/readyForMarking/idgroup/{}.png".format(examsGrouped[n][0])
    )
    # then all the group images
    # get the TGV and filename from the examsgrouped json.
    for pg in range(spec.getNumberOfGroups()):
        # note pg is offset by 1.
        # then filename = Gxxxxgyyvzz.png for tgv  txxxxgyyvz
        # so replace first char by G
        imgl.append(
            "../imageServer/markedPapers/G{}.png".format(examsGrouped[n][pg + 1][1:])
        )
    return imgl


# read the test spec.
spec = TestSpecification()
spec.readSpec()
# Read in the completed exams, the ID'd exams and grouped exams.
readExamsCompleted()
readExamsIDed()
readExamsGrouped()
outdir = "reassembled"
# Open a file for a list of commands to process to reassemble papers.
fh = open("./commandlist.txt", "w")
# Look at all the successfully completed exams
for n in sorted(examsCompleted.keys()):
    if examsCompleted[n]:
        cover = "coverPages/cover_{}.pdf".format(n.zfill(4))
        fh.write(
            'python3 testReassembler.py {} {} {} {} "{}"\n'.format(
                spec.Name, examsIDed[n][1], outdir, cover, imageList(n)
            )
        )
fh.close()
# pipe commands through gnu-parallel
os.system("parallel --bar <commandlist.txt")
# then delete command file.
os.unlink("commandlist.txt")
