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


def readExamsScanned():
    """Read which TPV have been scanned."""
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open("../resources/examsScanned.json") as data_file:
            examsScanned = json.load(data_file)


def readExamsGrouped():
    """Read which test/page/versions have been grouped
    into test/group/version images.
    To avoid reprocessing
    """
    global examsGrouped
    if os.path.exists("../resources/examsGrouped.json"):
        with open("../resources/examsGrouped.json") as data_file:
            examsGrouped = json.load(data_file)


def writeExamsGrouped():
    """Write the list of test/group/version that have been grouped"""
    eg = open("../resources/examsGrouped.json", "w")
    eg.write(json.dumps(examsGrouped, indent=2, sort_keys=True))
    eg.close()


def groupTest(t):
    """Group page images together using imagemagick montage
    Pages in a given test/pagegroup are glued together into
    a single image for marking.
    """
    # List of groups created for this test number
    examsGrouped[t] = []
    ts = str(t)
    # The montage command takes each page image as input
    # plus we put a border around things.
    # First do the idpages (ie pagegroup 0)
    montCommand = "montage -quiet"
    # since there may be more than 1 id-page.
    for p in spec.IDGroup:
        ps = str(p)
        v = 1
        montCommand += " page_{}/version_{}/t{}p{}v{}.png".format(
            ps.zfill(2), v, ts.zfill(4), ps.zfill(2), v
        )
    # put a small border around each pageimage
    montCommand += " -border 5 -geometry +1+{:d}".format(len(spec.IDGroup))
    # output to readyForMarking
    montCommand += " ../readyForMarking/idgroup/t{}idg.png\n".format(ts.zfill(4))
    # Add the idpage file to the list of things grouped.
    examsGrouped[t].append("t{:s}idg".format(ts.zfill(4)))

    # Now we do similarly for each page-group
    for k in range(1, spec.getNumberOfGroups() + 1):
        montCommand += "montage -quiet"
        pg = spec.PageGroups[k]
        for p in pg:
            ps = str(p)
            v = examsScanned[ts][ps][0]
            montCommand += " page_{}/version_{}/t{}p{}v{}.png".format(
                ps.zfill(2), v, ts.zfill(4), ps.zfill(2), v
            )
        # put a border around things.
        montCommand += " -border 5 -tile {}x1 -geometry +1+{}".format(len(pg), len(pg))
        # and output to readyForMarking
        montCommand += (
            " ../readyForMarking/group_{}/version_{}/"
            "t{}g{}v{}.png\n".format(
                str(k).zfill(2), v, ts.zfill(4), str(k).zfill(2), v
            )
        )
        # Append this pagegroup to the list of things grouped.
        examsGrouped[t].append("t{}g{}v{}".format(ts.zfill(4), str(k).zfill(2), v))
    # Now return the big list of montage commands as a multiline string.
    return montCommand


def checkTestComplete(t):
    """Similar to function in 05 script. Checks to see if
    all pages present in the current test. If not print error
    and return false."""
    # Check for each page in the scans of the given test
    for p in range(1, spec.Length + 1):
        # if anything missing return False
        if str(p) not in examsScanned[t]:
            return False
    # Else return true.
    return True


def checkTests():
    """Check the list of scanned tpv to work our which are ready
    for grouping (ie duplicating 05 script). If complete then
    use imagemagick to glue pages from each pagegroup together
    """
    # The list of tests to group.
    readyToGroup = []
    # Check the scan-list for complete tests
    for t in examsScanned:
        # check if test is complete.
        if checkTestComplete(t):
            readyToGroup.append(t)
    # Build a list of commands to run via gnu-parallel.
    commandList = ""
    # Go through list of ready-to-group test
    for t in readyToGroup:
        # If given test is already grouped then skip.
        if t in examsGrouped:
            print(">> Exam {:s} already grouped.".format(t))
            # At present user has to hack the relevant json
            # file to regroup a given test.
        else:
            # Add the test-grouping command to the list.
            commandList += groupTest(t)
    # Go into the relevant directory
    os.chdir("decodedPages")
    # Write the grouping command to file
    fh = open("commandlist.txt", "w")
    fh.write(commandList)
    fh.close()
    # Run it through gnu-parallel and then delete.
    os.system("parallel --bar < commandlist.txt")
    os.unlink("commandlist.txt")
    os.chdir("../")


spec = TestSpecification()
spec.readSpec()
examsScanned = defaultdict(dict)
examsGrouped = defaultdict(list)
readExamsScanned()
readExamsGrouped()
checkTests()
writeExamsGrouped()
