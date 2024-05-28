# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

import json
import logging
from multiprocessing import Pool
from pathlib import Path
import shutil

from tqdm import tqdm

from plom.tpv_utils import (
    parseTPV,
    isValidTPV,
    getCode,
    getPosition,
)
from plom.scan import with_scanner_messenger
from plom.scan import QRextract_legacy
from plom.scan.rotate import rotate_bitmap
from plom import PlomImageExts


log = logging.getLogger("scan")


def decode_QRs_in_image_files(where):
    """Find all bitmaps in pageImages dir and decode their QR codes.

    If their QRcodes have not been successfully decoded previously
    then decode them.  The results are stored in blah.<ext>.qr files.

    Args:
        where (str, Path): where to search, e.g., "bundledir/pageImages"
    """
    stuff = []
    for ext in PlomImageExts:
        stuff.extend(where.glob(f"*.{ext}"))
    N = len(stuff)
    with Pool() as p:
        _ = list(tqdm(p.imap_unordered(QRextract_legacy, stuff), total=N))
    # This does the same as the following serial loop but in parallel
    # for x in glob.glob(...):
    #     QRextract_legacy(x)


def reOrientPage(fname, qrs):
    """Re-orient this page if needed, changing the image file on disk.

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
    # "actions" refer to the CCW rotation we apply to fixed the observed
    # rotation.  E.g., if we observe "rot90cc" then we need to perform a
    # 90 cw rotation, which is -90 ccw; the value of the action.
    actions = {
        "upright": 0,
        "rot90cw": 90,
        "rot90cc": -90,
        "flipped": 180,
    }

    # fake a default_dict, flake8 does not like, consider using function
    g = lambda x: getPosition(qrs.get(x)) if qrs.get(x, None) else None  # noqa: E731
    current = [g("NE"), g("NW"), g("SW"), g("SE")]

    def comp(A, B):
        """Compare two lists ignoring any positions with Nones."""
        return all([x == y for x, y in zip(A, B) if x and y])

    matches = {k: comp(v, current) for (k, v) in targets.items() if comp(v, current)}
    if len(matches) != 1:
        return False
    match_key, v = matches.popitem()
    rotate_bitmap(fname, actions[match_key])
    return True


def checkQRsValid(bundledir, spec):
    """Check that the QRcodes in each pageimage are valid.

    When each bitmap was scanned a .qr was produced.  Load the dict of
    QR codes from that file and do some sanity checks.

    Rotate any images that we can.

    Args:
        bundledir (str, Path): look for images in the subdir
            `bundledir/pageImages` and other subdirs.
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.

    Returns:
        dict: keys are filenames of images; values are ``(t, p, v)``.

    TODO: maybe we should split this function up a bit!

    TODO: some Android scanning apps place a QR code on each page.
    Perhaps we should discard non-Plom codes before other processing
    instead of that being an error.
    """
    examsScannedNow = {}

    # go into page image directory of each bundle and look at each .qr file.
    for fnqr in (bundledir / "pageImages").glob("*.qr"):
        msg = ""
        fname = fnqr.with_suffix("")  # strip .qr from blah.<ext>.qr
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
        for d, qr in qrs.items():
            if len(qr) == 1:
                tmp[d] = qr[0]
        qrs = tmp
        del tmp

        if len(qrs) == 0:
            msg = "No QR codes were decoded."
            problemFlag = True

        if not problemFlag:
            for tpvc in qrs.values():
                if tpvc in [f"plomX{n}" for n in range(1, 9)]:
                    msg = f"Is >> extra page << with code '{tpvc}' - todo orient and file differently"
                    problemFlag = True
                elif not isValidTPV(tpvc):
                    msg = "TPV '{}' is not a valid format".format(tpvc)
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
        tgvs = []
        if not problemFlag:
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
                # riskiness = 10
                # tgv = tgvs[0]
            elif len(tgvs) == 2:
                msg = "Only two of three QR codes decoded."
                warnFlag = True
                # riskiness = 1
                # tgv = tgvs[0]
            elif len(tgvs) == 3:
                pass
                # full consensus
                # tgv = tgvs[0]
            else:  # len > 3, shouldn't be possible now
                msg = "Too many QR codes on the page!"
                problemFlag = True

        if not problemFlag:
            if warnFlag:
                explain = "(high occurrences of these warnings may mean printer/scanner problems)"
                print(f"[W] {fname}: {msg}\n    {explain}")
                log.warning(f"[W] {fname}: {msg}\n    {explain}")

        if not problemFlag:
            problemFlag, msg = validateQRsAgainstSpec(
                spec, fname, tn, pn, vn
            )  # pyright: ignore

        if not problemFlag:
            # we have a valid TGVC and the code matches.
            examsScannedNow[fname] = [tn, pn, vn]
        else:
            # Difficulty scanning this pageimage so move it to unknownPages
            # fname =  bname/pageImages/blah-n.png
            # dest = bname/unknownPages/blah-n.png
            dest = bundledir / "unknownPages" / fname.name
            print(f"[F] {fname}: {msg}  Moving to unknownPages")
            log.warning(f"[F] {fname}: {msg}  Moving to unknownPages")
            # move blah.<ext> and blah.<ext>.qr
            shutil.move(fname, dest)
            shutil.move(Path(str(fname) + ".qr"), Path(str(dest) + ".qr"))
    return examsScannedNow


def validateQRsAgainstSpec(spec, fname, t, p, v):
    """Do some kind of checking and someday document it better.

    After pageimages have been decoded we need to check the results
    against the spec. A simple check of test-name and magic-code were
    done already, but now the test-page-version triples are checked.

    TODO: shouldn't this be more serious?  Issue #2114.
    """
    errs = []
    if t < 1 or t > spec["numberToProduce"]:
        # TODO: Issue #1745
        errs.append("t outside [1, {}]".format(spec["numberToProduce"]))
    if p < 1 or p > spec["numberOfPages"]:
        errs.append("p outside [1, {}]".format(spec["numberOfPages"]))
    if v < 1 or v > spec["numberOfVersions"]:
        errs.append("v outside [1, {}]".format(spec["numberOfVersions"]))
    if errs:
        msg = f'Mismatch b/w scan "t{t}p{p}v{v}" and spec: {"; ".join(errs)}'
        return True, msg
    return False, ""


def moveScansIntoPlace(bundledir, examsScannedNow):
    # For each test we have just scanned
    for fname in examsScannedNow:
        t = examsScannedNow[fname][0]
        p = examsScannedNow[fname][1]
        v = examsScannedNow[fname][2]

        dpath = bundledir / "decodedPages"
        # move blah-n.png to txxxxpyyvz.blah-n.png
        dest = dpath / f"t{t:04}p{p:02}v{v}.{fname.name}"
        log.info("Successfully decoded QRs: moving %s to %s", fname.name, dest)
        shutil.move(fname, dest)
        shutil.move(Path(str(fname) + ".qr"), Path(str(dest) + ".qr"))


@with_scanner_messenger
def processBitmaps(bundledir, *, msgr):
    spec = msgr.get_spec()

    decode_QRs_in_image_files(bundledir / "pageImages")
    examsScannedNow = checkQRsValid(bundledir, spec)
    moveScansIntoPlace(bundledir, examsScannedNow)
