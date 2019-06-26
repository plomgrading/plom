__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin MacDonald", "Elvis Cai"]
__license__ = "AGPLv3"

from collections import defaultdict
import glob
import json
import os
import re
import shutil
import sys

# this allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


def decodeQRs():
    """Go into pageimage directory
    Look at all the png files
    If their QRcodes have not been successfully decoded previously
    then decode them using extractQRAndOrient script.
    The results are stored in blah.png.qr files.
    Commands piped through gnu-parallel.
    """
    os.chdir("./pageImages/")
    fh = open("commandlist.txt", "w")
    for fname in glob.glob("*.png"):
        # If the .qr file does not exist, or if it has length 0
        # then run extract/orient script on that png.
        if (not os.path.exists(fname + ".qr")) or os.path.getsize(fname + ".qr") == 0:
            fh.write("python3 ../extractQRAndOrient.py {}\n".format(fname))
    fh.close()
    # run those commands through gnu-parallel then delete.
    os.system("parallel --bar < commandlist.txt")
    os.unlink("commandlist.txt")
    os.chdir("../")


def readExamsProduced():
    """Read the exams that were produced during build"""
    global examsProduced
    with open("../resources/examsProduced.json") as data_file:
        examsProduced = json.load(data_file)


def readExamsScanned():
    """Read the list of test/page/versions that have been scanned"""
    global examsScanned
    if os.path.exists("../resources/examsScanned.json"):
        with open("../resources/examsScanned.json") as data_file:
            examsScanned = json.load(data_file)


def writeExamsScanned():
    """Update the list of test/page/versions that have been scanned"""
    es = open("../resources/examsScanned.json", "w")
    es.write(json.dumps(examsScanned, indent=2, sort_keys=True))
    es.close()


def checkQRsValid():
    """Check that the QRcodes in each pageimage are valid.
    When each png is scanned a png.qr is produced.
    Those should have 3 lines each - 2x tpv and 1x name.
    Valid lines are either "QR-Code:tXpYvZ" or "QR-Code:N:X"
    """
    # Build regular expressions for checking the QR codes.
    patternCode = re.compile(r"QR-Code:(t\d+)(p\d+)(v\d+)")
    patternName = re.compile(r"QR-Code:N.\w+")
    # go into page image directory and look at each .qr file.
    os.chdir("pageImages/")
    for fname in glob.glob("*.qr"):
        fin = open(fname, "r")
        lines = []
        codeFlag = 0
        nameFlag = 0
        # check each line in the .qr file
        for line in fin:
            line = line.rstrip("\n")
            lines.append(line)
            # check if is test-name code N.blah and extract name
            if patternName.match(line):
                nameFlag += 1
                testName = line[10:]
            # check if is tpv code tXpYvZ
            if patternCode.match(line):
                # a valid line will be "QR-Code:tXpYvZ"
                # store as code=[0,X,Y,Z]
                code = re.split(r"\D", line[8:])
                codeFlag += 1
        # If we found a name and a tpv file, and the name matches the
        # name in the test-specification then store the tpv in examsScannedNow
        # later we check that list against those produced during build
        if nameFlag == 1 and codeFlag == 1 and testName == spec.Name:
            # Convert X,Y,Z to ints and make note it has been scanned.
            # store as esn[testnumber][pagenumber] = [version, blah.png]
            examsScannedNow[int(code[1])][int(code[2])] = (int(code[3]), fname[:-3])
        else:
            # Difficulty scanning this pageimage so move it
            # to problemimages
            print(
                "A problem with codes in {} and " "testname {}".format(fname, testName)
            )
            # move blah.png.qr
            shutil.move(fname, "problemImages")
            # move blah.png
            shutil.move(fname[:-3], "problemImages")
    os.chdir("../")


def validateQRsAgainstProduction():
    """After pageimages have been decoded we need to check the
    results against the TPVs that constructed during build.
    A simple check of test-name was done already, but now
    the test-page-version triples are checked.
    """
    # go into page images directory
    os.chdir("./pageImages")
    # for each test-number that was scanned on this run of this script
    # check that the tpv matches the one recorded during build.
    for t in examsScannedNow.keys():
        # create string of t for json matching.
        ts = str(t)
        # for each page of that test-number
        for p in examsScannedNow[t].keys():
            # again create string of p for json matching.
            ps = str(p)
            # the version of that test/page
            v = examsScannedNow[t][p][0]
            # the corresponding page imge file name
            fn = examsScannedNow[t][p][1]
            # if the tpv's match then all good.
            if examsProduced[ts][ps] == v:
                # print success and thats all.
                print(
                    "Valid scan of t{:s} p{:s} v{:d} from file {:s}".format(
                        ts, ps, v, fn
                    )
                )
            else:
                # print mismatch warning and move file to problem-images
                print(">> Mismatch between exam scanned and exam produced")
                print(
                    ">> Produced t{:s} p{:s} v{:d}".format(
                        ts, ps, examsProduced[ts][ps]
                    )
                )
                print(
                    ">> Scanned t{:s} p{:s} v{:d} from file {:s}".format(ts, ps, v, fn)
                )
                print(">> Moving problem files to problemImages")
                # move the blah.png and blah.png.qr
                # this means that they won't be added to the
                # list of correctly scanned page images
                shutil.move(fn, "problemImages")
                shutil.move(fn + ".qr", "problemImages")
                # Remove page from the exams-scanned-now list.
                examsScannedNow[ts].pop(ps)
    os.chdir("../")


def addCurrentScansToExamsScanned():
    os.chdir("./pageImages")
    # For each test we have just scanned
    for t in examsScannedNow.keys():
        ts = str(t)  # for json keys
        # if it is not in the previous scan batch
        # create an entry for it.
        if ts not in examsScanned:
            examsScanned[ts] = {}
        # For each page in this test
        for p in examsScannedNow[t].keys():
            ps = str(p)  # for json keys
            # grab the version and filename
            v = examsScannedNow[t][p][0]
            fn = examsScannedNow[t][p][1]
            # If we have seen this test/page before then
            # we will overwrite the old one but issue a warning
            if ps in examsScanned[ts]:
                # Eventually we should output this sort of thing to
                # a log file in case of user-errors.
                print(
                    ">> Have already scanned t{:s}p{:s}v{:d} in file {:s}".format(
                        ts, ps, v, fn
                    )
                )
                print(">> Will overwrite with new version")
                examsScanned[ts][ps] = examsScannedNow[t][p]
            else:
                # This is a new test/page so add it to the scan-list
                examsScanned[ts][ps] = examsScannedNow[t][p]
                # copy the file into place
                # eventually we should move it instead of copying it.
                # save on disc space?
                shutil.copy(
                    fn,
                    "../decodedPages/page_{}/version_{}/t{}p{}v{}.png".format(
                        str(p).zfill(2),
                        str(v),
                        str(t).zfill(4),
                        str(p).zfill(2),
                        str(v),
                    ),
                )
            # move the filename into alreadyProcessed
            shutil.move(fn, "alreadyProcessed")
            shutil.move(fn + ".qr", "alreadyProcessed")
    os.chdir("../")


examsProduced = {}
examsScanned = defaultdict(dict)
examsScannedNow = defaultdict(dict)
spec = TestSpecification()
spec.readSpec()
readExamsProduced()
readExamsScanned()
decodeQRs()
checkQRsValid()
validateQRsAgainstProduction()
addCurrentScansToExamsScanned()
writeExamsScanned()
