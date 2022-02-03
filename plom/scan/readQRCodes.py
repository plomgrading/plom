# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from collections import defaultdict
import json
import os
import shutil
from multiprocessing import Pool
from pathlib import Path

from tqdm import tqdm

from plom.tpv_utils import (
    parseTPV,
    isValidTPV,
    hasCurrentAPI,
    getCode,
    getPosition,
)
from plom.scan import with_scanner_messenger
from plom.scan import QRextract
from plom.scan.rotate import rotateBitmap
from plom import PlomImageExts


def decode_QRs_in_image_files(where):
    """Find all bitmaps in pageImages dir and decode their QR codes.

    If their QRcodes have not been successfully decoded previously
    then decode them.  The results are stored in blah.<ext>.qr files.

    Args:
        where (str, Path): where to search, e.g., "bundledir/pageImages"
    """
    stuff = []
    for ext in PlomImageExts:
        stuff.extend(where.glob("*.{}".format(ext)))
    N = len(stuff)
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(QRextract, stuff), total=N))
    # This does the same as the following serial loop but in parallel
    # for x in glob.glob(...):
    #     QRextract(x)


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

        1----4    4---3    3----2
        |    |    |   |    |    |
        2----3    |   |    4----1
                  1---2

    Args:
       fname (str): the bitmap filename of this page.  Either its the FQN
                    or we are currently in the right directory.
       qrs (dict): the QR codes of the four corners.  Some or all may
                   be missing.

    Returns:
       bool: True if the image was already upright or has now been
             made upright.  False if the image is in unknown
             orientation or we have contradictory information.

    """
    targets = {
        "upright": [1, 2, 3, 4],  # [NE, NW, SW, SE]
        "rot90cw": [2, 3, 4, 1],
        "rot90cc": [4, 1, 2, 3],
        "flipped": [3, 4, 1, 2],
    }
    actions = {
        "upright": 0,
        "rot90cw": -90,
        "rot90cc": 90,
        "flipped": 180,
    }

    # fake a default_dict, flake8 does not like, consider using function
    g = lambda x: getPosition(qrs.get(x)) if qrs.get(x, None) else None  # noqa: E731
    current = [g("NE"), g("NW"), g("SW"), g("SE")]

    def comp(A, B):
        """compare two lists ignoring any positions with Nones"""
        return all([x == y for x, y in zip(A, B) if x and y])

    matches = {k: comp(v, current) for (k, v) in targets.items() if comp(v, current)}
    if len(matches) != 1:
        return False
    match_key, v = matches.popitem()
    rotateBitmap(fname, actions[match_key])
    return True


def checkQRsValid(bundledir, spec, examsScannedNow):
    """Check that the QRcodes in each pageimage are valid.

    When each bitmap is scanned a .qr is produced.  Load the dict of
    QR codes from that file and do some sanity checks.

    Rotate any images that we can.

    Args:
        bundledir (str, Path): look for images in the subdir
            `bundledir/pageImages` and other subdirs.
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        examsScannedNow: TODO?

    TODO: maybe we should split this function up a bit!

    TODO: some Android scanning apps place a QR code on each page.
    Perhaps we should discard non-Plom codes before other processing
    instead of that being an error.
    """
    # go into page image directory of each bundle and look at each .qr file.
    for fnqr in (bundledir / "pageImages").glob("*.qr"):
        # fname = fnqr.stem  # strip .qr from blah.<ext>.qr
        fname = Path(str(fnqr)[0:-3])  # Yuck, TODO
        with open(fnqr, "r") as qrfile:
            qrs = json.load(qrfile)

        problemFlag = False
        warnFlag = False

        # Flag papers that have too many QR codes in some corner
        if any(len(x) > 1 for x in qrs.values()):
            msg = "Too many QR codes in some corner (debug: qrs is {})".format(str(qrs))
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
            orientationKnown = reOrientPage(fname, qrs)
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
                    "   (high occurrences of these warnings may mean printer/scanner problems)"
                )
            # store the tpv in examsScannedNow
            examsScannedNow[fname] = [tn, pn, vn]
            # later we check that list against those produced during build

        if problemFlag:
            # Difficulty scanning this pageimage so move it to unknownPages
            # fname =  bname/pageImages/blah-n.png
            # dst = bname/unknownPages/blah-n.png
            [prefix, suffix] = os.path.split(
                fname
            )  # pref = "bname/pageImages", suf = blah-n.png
            dst = os.path.join(os.path.split(prefix)[0], "unknownPages", suffix)

            print("[F] {0}: {1} - moving to unknownPages".format(fname, msg))
            # move blah.<ext> and blah.<ext>.qr
            shutil.move(fname, dst)
            # TODO: better with some `.with_suffix()` juggling
            # TODO: there are at least two other places
            shutil.move(Path(str(fname) + ".qr"), Path(str(dst) + ".qr"))


def validateQRsAgainstSpec(spec, examsScannedNow):
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
        if t < 0 or t > spec["numberToProduce"]:
            flag = False
        if p < 0 or p > spec["numberOfPages"]:
            flag = False
        if v < 0 or v > spec["numberOfVersions"]:
            flag = False
        if not flag:
            print(">> Mismatch between page scanned and spec - this should NOT happen")
            print(f">> Produced t{t} p{p} v{v}")
            print(
                ">> Must have t-code in [1,{}], p-code in [1,{}], v-code in [1,{}]".format(
                    spec["numberToProduce"],
                    spec["numberOfPages"],
                    spec["numberOfVersions"],
                )
            )
            print(">> Moving problem files to unknownPages")
            # fname =  bname/pageImages/blah-n.png
            # dst = bname/unknownPages/blah-n.png
            [prefix, suffix] = os.path.split(
                fname
            )  # pref = "bname/pageImages", suf = blah-n.png
            dst = os.path.join(os.path.split(prefix)[0], "unknownPages", suffix)

            print(f"[F] {fname}: moving to unknownPages")
            # move the blah.<ext> and blah.<ext>.qr
            # this means that they won't be added to the
            # list of correctly scanned page images
            shutil.move(fname, dst)
            # TODO: better with some `.with_suffix()` juggling
            # TODO: there are at least two other places
            shutil.move(Path(str(fname) + ".qr"), Path(str(dst) + ".qr"))


def moveScansIntoPlace(examsScannedNow):
    # For each test we have just scanned
    for fname in examsScannedNow:
        t = examsScannedNow[fname][0]
        p = examsScannedNow[fname][1]
        v = examsScannedNow[fname][2]

        [prefix, suffix] = os.path.split(
            fname
        )  # pref = "bname/pageImages", suf = blah-n.png
        dpath = os.path.join(os.path.split(prefix)[0], "decodedPages")
        # move blah-n.png to txxxxpyyvz.blah-n.png
        dname = "t{}p{}v{}.{}".format(str(t).zfill(4), str(p).zfill(2), str(v), suffix)
        shutil.move(fname, os.path.join(dpath, dname))
        # TODO: better with some `.with_suffix()` juggling
        # TODO: there are at least two other places
        shutil.move(
            Path(str(fname) + ".qr"), os.path.join(dpath, Path(str(dname) + ".qr"))
        )


@with_scanner_messenger
def processBitmaps(bundle, *, msgr):
    examsScannedNow = defaultdict(list)

    spec = msgr.get_spec()

    decode_QRs_in_image_files(bundle / "pageImages")
    checkQRsValid(bundle, spec, examsScannedNow)
    validateQRsAgainstSpec(spec, examsScannedNow)
    moveScansIntoPlace(examsScannedNow)
