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


def readGroupImagesMarked():
    """Read json of marked'd tests. Store in examsMarked.
    Indexed by [testnumber][pagegroup], stores mark and version number.
    """
    global groupImagesMarked
    if os.path.exists("../resources/groupImagesMarked.json"):
        with open("../resources/groupImagesMarked.json") as data_file:
            groupImagesMarked = json.load(data_file)


def extractMarks(n):
    """Grab the marks for testnumber n and store in examScores as list of
    triples [group, version, mark]
    """
    for pg in range(1, spec.getNumberOfGroups() + 1):
        pgs = str(pg)
        v = groupImagesMarked[n][pgs][0]
        examScores[n].append([pg, v, groupImagesMarked[n][pgs][1]])


def buildCoverPage(n):
    """Construct string of command to pass to the coverPageBuilder script.
    Script needs [TestNumber, Name, ID,]
    and then for each group [group, version, mark, maxPossibleMark]
    """
    arg = []
    sname = examsIDed[n][2]
    sid = examsIDed[n][1]
    arg.append(int(n))
    arg.append(sname)
    arg.append(int(sid))
    # Each entry in exam scores is a list of [group, version, mark]
    for x in examScores[n]:
        arg.append([x[0], x[1], x[2], spec.Marks[x[0]]])
    # return string of the command.
    return 'python3 coverPageBuilder.py "{}"\n'.format(arg)


# read test specification
spec = TestSpecification()
spec.readSpec()
# build dictionaries for exam lists
examsCompleted = {}
examScores = defaultdict(list)
# read in the list of completed exams and the ID's and marks.
readExamsCompleted()
readExamsIDed()
readGroupImagesMarked()
os.makedirs("coverPages", exist_ok=True)
# Build a list of command to pipe into gnu-parallel.
fh = open("./commandlist.txt", "w")
for n in sorted(examsCompleted.keys()):
    s = "" + n
    if examsCompleted[n]:
        # If coverpage hasn't been built before
        # TODO: should check if anything actually changed...
        # https://gitlab.math.ubc.ca/andrewr/MLP/issues/392
        if not os.path.isfile("./coverPages/cover_{}.pdf".format(str(n).zfill(4))):
            # extract the info for test n
            extractMarks(n)
            # write the corresponding command to file.
            fh.write(buildCoverPage(n))
fh.close()
# Run all the commands through gnu-parallel
os.system("parallel --bar <commandlist.txt")
# Delete the command file.
os.unlink("commandlist.txt")
