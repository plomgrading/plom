#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

from collections import defaultdict
import getpass
import glob
import json
import os
import shutil
import subprocess
import toml

from tpv_utils import (
    parseTPV,
    isValidTPV,
    hasCurrentAPI,
    getCode,
    getPosition,
)
import scanMessenger


def buildDirectories():
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["decodedPages", "unknownPages"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


def decodeQRs():
    """Go into pageimage directory
    Look at all the png files
    If their QRcodes have not been successfully decoded previously
    then decode them using another script.
    The results are stored in blah.png.qr files.
    Commands piped through gnu-parallel.
    """
    os.chdir("./pageImages/")
    fh = open("commandlist.txt", "w")
    for fname in glob.glob("*.png"):
        # If the .qr file does not exist, or if it has length 0
        # then run extract/orient script on that png.
        if (not os.path.exists(fname + ".qr")) or os.path.getsize(fname + ".qr") == 0:
            fh.write("python3 ../fasterQRExtract.py {}\n".format(fname))
    fh.close()
    # run those commands through gnu-parallel then delete.
    subprocess.run(
        ["parallel", "--bar", "-a", "commandlist.txt"],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )
    # os.system("parallel --bar < commandlist.txt")
    os.unlink("commandlist.txt")
    os.chdir("../")


def reOrientPage(fname, qrs):
    """Re-orient this page if needed

    If a page is upright, a subset of the QR codes 1 through 4 are on
    the corners:

        2---1   NW---NE
        |   |    |   |
        |   |    |   |
        3---4   SW---SE

    We use this known configuration to recognize rotations.  Either 1
    or 2 is missing (because of the staple area) and we could be
    missing others.

    Assuming reflection combined with missing QR codes is an unlikely
    scenario, we can orient even if we know only one corner.

    Args:
       fname (str): the png filename of this page.  Either its the FQN
                    or we are currently in the right directory.
       qrs (dict): the QR codes of the four corners.  Some or all may
                   be missing.

    Returns:
       bool: True if the image was already upright or has now been
             made upright.  False if the image is in unknown
             orientation or we have contradictory information.

    """
    upright = [1, 2, 3, 4]  # [NE, NW, SW, SE]
    flipped = [3, 4, 1, 2]
    # fake a default_dict
    g = lambda x: getPosition(qrs.get(x)) if qrs.get(x, None) else -1
    current = [g("NE"), g("NW"), g("SW"), g("SE")]
    # now compare as much as possible of current against upright/flipped ignoring -1s
    upFlag = True
    flipFlag = True
    for k in range(4):
        if current[k] == -1:
            continue
        if upright[k] == current[k]:
            flipFlag = False
        if flipped[k] == current[k]:
            upFlag = False

    if upFlag and not flipFlag:
        # is upright, no rotation needed
        return True
    if flipFlag and not upFlag:
        # is flipped, so rotate 180
        # print(" .  {}: reorienting: 180 degree rotation".format(fname))
        subprocess.run(
            ["mogrify", "-quiet", "-rotate", "180", fname],
            stderr=subprocess.STDOUT,
            shell=False,
            check=True,
        )
        return True
    else:
        # either not enough info or conflicting info
        return False


def checkQRsValid():
    """Check that the QRcodes in each pageimage are valid.

    When each png is scanned a png.qr is produced.  Load the dict of
    QR codes from that file and do some sanity checks.

    Rotate any images that we can.

    TODO: maybe we should split this function up a bit!
    """
    # go into page image directory and look at each .qr file.
    os.chdir("pageImages/")
    for fnqr in glob.glob("*.qr"):
        fname = fnqr[:-3]  # blah.png.qr -> blah.png
        with open(fnqr, "r") as qrfile:
            qrs = json.load(qrfile)

        problemFlag = False
        warnFlag = False

        # Flag papers that have too many QR codes in some corner
        # TODO: untested?
        if any(len(x) > 1 for x in qrs.values()):
            msg = "Too many QR codes in {} corner".format(x)
            problemFlag = True

        # Unpack the lists of QRs, building a new dict with only the
        # the corners with exactly one QR code.
        tmp = {}
        for (d, qr) in qrs.items():
            if len(qr) == 1:
                tmp[d] = qr[0]
        qrs = tmp
        del tmp

        if len(qrs) == 0:
            msg = "No QR codes were decoded."
            problemFlag = True

        if not problemFlag:
            for tpvc in qrs.values():
                if not isValidTPV(tpvc):
                    msg = "TPV '{}' is not a valid format".format(tpvc)
                    problemFlag = True
                elif not hasCurrentAPI(tpvc):
                    msg = "TPV '{}' does not match API.  Legacy issue?".format(tpvc)
                    problemFlag = True
                elif str(getCode(tpvc)) != str(spec["publicCode"]):
                    msg = (
                        "Magic code '{0}' did not match spec '{1}'.  "
                        "Did you scan the wrong test?".format(
                            getCode(tpvc), spec["publicCode"]
                        )
                    )
                    problemFlag = True

        # Make sure all (t,p,v) on this page are the same
        if not problemFlag:
            tgvs = []
            for tpvc in qrs.values():
                tn, pn, vn, cn, o = parseTPV(tpvc)
                tgvs.append((tn, pn, vn))

            if not len(set(tgvs)) == 1:
                # Decoder either gives the correct code or no code at all
                # Perhaps if you see this, its a folded page
                msg = "Multiple different QR codes! (rare in theory: folded page?)"
                problemFlag = True

        if not problemFlag:
            orientationKnown = reOrientPage(fname[:-3], qrs)
            # TODO: future improvement: could keep going, its possible
            # we can go on to find the (t,p,v) in some cases.
            if not orientationKnown:
                msg = "Orientation not known"
                problemFlag = True

        # Decide in which cases we can be confident we know this papers (t,p,v)
        if not problemFlag:
            if len(tgvs) == 1:
                msg = "Only one of three QR codes decoded."
                # TODO: in principle could proceed, albeit dangerously
                warnFlag = True
                riskiness = 10
                tgv = tgvs[0]
            elif len(tgvs) == 2:
                msg = "Only two of three QR codes decoded."
                warnFlag = True
                riskiness = 1
                tgv = tgvs[0]
            elif len(tgvs) == 3:
                # full consensus
                tgv = tgvs[0]
            else:  # len > 3, shouldn't be possible now
                msg = "Too many QR codes on the page!"
                problemFlag = True

        if not problemFlag:
            # we have a valid TGVC and the code matches.
            if warnFlag:
                print("[W] {0}: {1}".format(fname, msg))
                print(
                    "   (high occurences of these warnings may mean printer/scanner problems)"
                )
            # store the tpv in examsScannedNow
            examsScannedNow[fname] = [tn, pn, vn]
            # later we check that list against those produced during build

        if problemFlag:
            # Difficulty scanning this pageimage so move it
            # to unknownPages
            print("[F] {0}: {1} - moving to unknownPages".format(fname, msg))
            # move blah.png and blah.png.qr
            shutil.move(fname, "../unknownPages/" + fname)
            shutil.move(fname + ".qr", "../unknownPages/" + fname + ".qr")

    os.chdir("../")


def validateQRsAgainstSpec(spec):
    """After pageimages have been decoded we need to check the results
    against the spec. A simple check of test-name and magic-code were
    done already, but now the test-page-version triples are checked.
    """
    for fname in examsScannedNow:
        t = examsScannedNow[fname][0]
        p = examsScannedNow[fname][1]
        v = examsScannedNow[fname][2]
        # make a valid flag
        flag = True
        if t < 0 or t > spec["numberOfTests"]:  # slight bastardisation of normal spec
            flag = False
        if p < 0 or p > spec["numberOfPages"]:
            flag = False
        if v < 0 or v > spec["numberOfVersions"]:
            flag = False
        if not flag:
            print(">> Mismatch between page scanned and spec - this should NOT happen")
            print(">> Produced t{} p{} v{}".format(t, p, tfv[1]))
            print(
                ">> Must have t-code in [1,{}], p-code in [1,{}], v-code in [1,{}]".format(
                    spec["numberOfTests"],
                    spec["numberOfPages"],
                    spec["numberOfVersions"],
                )
            )
            print(">> Moving problem files to unknownPages")
            # move the blah.png and blah.png.qr
            # this means that they won't be added to the
            # list of correctly scanned page images
            shutil.move(fn, "../unknownPages")
            shutil.move(fn + ".qr", "../unknownPages")


def moveScansIntoPlace():
    os.chdir("./pageImages")
    # For each test we have just scanned
    for fname in examsScannedNow:
        t = examsScannedNow[fname][0]
        p = examsScannedNow[fname][1]
        v = examsScannedNow[fname][2]

        destName = "../decodedPages/t{}p{}v{}.{}".format(
            str(t).zfill(4), str(p).zfill(2), str(v), fname
        )
        shutil.move(fname, destName)
        shutil.move(fname + ".qr", destName + ".qr")

    os.chdir("../")


if __name__ == "__main__":
    examsScannedNow = defaultdict(list)
    scanMessenger.startMessenger()
    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    scanMessenger.requestAndSaveToken("scanner", pwd)
    spec = scanMessenger.getInfoGeneral()
    scanMessenger.closeUser()
    scanMessenger.stopMessenger()

    buildDirectories()
    decodeQRs()
    checkQRsValid()
    validateQRsAgainstSpec(spec)
    moveScansIntoPlace()
