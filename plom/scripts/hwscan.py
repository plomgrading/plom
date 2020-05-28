#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning homework and pushing to servers."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
from collections import defaultdict
import glob
import os
import shutil

from plom import __version__
from plom.rules import isValidStudentNumber


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def IDQorIDorBad(fullfname):
    fname = os.path.basename(fullfname)
    splut = fname.split(".")
    QFlag = splut[-2].isnumeric()
    IDFlag = isValidStudentNumber(splut[-3])
    if QFlag and IDFlag:  # [-3] is ID and [-2] is Q.
        return ["IDQ", splut[-3], splut[-2]]  # ID and Q
    elif isValidStudentNumber(splut[-2]):  # [-2] is ID
        return ["JID", splut[-2]]  # Just ID
    else:
        return ["BAD"]  # Bad format


def whoDidWhat():
    from plom.scan.hwSubmissionsCheck import whoSubmittedWhat

    whoSubmittedWhat()


def processScans(server, password, incomplete=False, extra=False):
    # make PDF archive directory
    os.makedirs("archivedPDFs/submittedHWByQ", exist_ok=True)
    os.makedirs("archivedPDFs/submittedHWExtra", exist_ok=True)
    # make a directory into which our (temp) PDF->bitmap will go
    os.makedirs("scanPNGs/submittedHWExtra", exist_ok=True)
    os.makedirs("scanPNGs/submittedHWByQ", exist_ok=True)
    # finally a directory into which pageImages go
    os.makedirs("decodedPages/submittedHWByQ", exist_ok=True)
    os.makedirs("decodedPages/submittedHWExtra", exist_ok=True)

    from plom.scan.hwSubmissionsCheck import verifiedComplete
    from plom.scan import scansToImages

    # process HWByQ first
    if incomplete:
        fileList = sorted(glob.glob("submittedHWByQ/*.pdf"))
    else:
        fileList = verifiedComplete(server, password)

    for fn in fileList:
        IDQ = IDQorIDorBad(fn)
        if len(IDQ) != 3:
            print("Skipping file {} - wrong format".format(fn))
            continue  # this is not the right file format
        print("Processing PDF {} to images".format(fn))
        scansToImages.processScans(fn, hwByQ=True)
    # then process HWExtra (if flagged)
    if extra:
        for fn in sorted(glob.glob("submittedHWExtra/*.pdf")):
            IDQ = IDQorIDorBad(fn)
            if len(IDQ) != 2:
                print("Skipping file {} - wrong format".format(fn))
                continue  # this is not the right file format
            print("Processing PDF {} to images".format(fn))
            scansToImages.processScans(fn, hwExtra=True)


def uploadHWImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer

    # make directories for upload
    os.makedirs("sentPages/submittedHWByQ", exist_ok=True)
    os.makedirs("sentPages/submittedHWExtra", exist_ok=True)

    print("Upload hw images to server")
    [SIDQ, SIDO] = sendPagesToServer.uploadHWPages(server, password)
    print(
        "Homework (by Q) was uploaded to the following studentIDs: {}".format(
            SIDQ.keys()
        )
    )
    print(
        "Homework (extra) was uploaded to the following studentIDs: {}".format(
            SIDO.keys()
        )
    )


parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command", description="Tools for dealing with scans.")
#
spW = sub.add_parser(
    "submitted",
    help="Get a list of SID and questions submitted in the submittedHomework directory.",
)
spP = sub.add_parser("process", help="Process scanned PDFs to images.")
spU = sub.add_parser("upload", help="Upload page images to scanner")
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser(
    "clear",
    help="Clear 'scanner' login",
    description="Clear 'scanner' login after a crash or other expected event.",
)
#
spP.add_argument(
    "-i",
    "--incomplete",
    action="store_true",
    default=False,
    help="Process incomplete homeworks (ie not all questions present)",
)
spP.add_argument(
    "-x",
    "--extra",
    action="store_true",
    default=False,
    help="Process extra pages for homeworks (ie one-file)",
)


for x in (spP, spU, spS, spC):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "submitted":
        whoDidWhat()
    elif args.command == "process":
        processScans(args.server, args.password, args.incomplete, args.extra)
    elif args.command == "upload":
        uploadHWImages(args.server, args.password)
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()
        print("\n>> Processing and uploading homework <<")
        print(">>>> WRITE DOCS <<<<")

    exit(0)


if __name__ == "__main__":
    main()
