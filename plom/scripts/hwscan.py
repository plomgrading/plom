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


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def extractIDQ(fileName):
    """Expecting filename of the form blah.SID.Q.pdf - return SID and Q"""
    splut = fileName.split(".")
    return (splut[-3], int(splut[-2]))


def whoDidWhat():
    subs = defaultdict(list)
    summary = defaultdict(list)
    for fn in glob.glob("submittedHomework/*.pdf"):
        sid, q = extractIDQ(fn)
        subs[sid].append(q)
    for sid in sorted(subs.keys()):
        summary[len(subs[sid])].append(sid)
        print("#{} submitted {}".format(sid, sorted(subs[sid])))
    print(">> summary <<")
    for s in summary:
        print("Students submitting {} items = {}".format(s, summary[s]))


def processScans():
    # make PDF archive directory
    os.makedirs("archivedPDFs/submittedHomework", exist_ok=True)
    # make a directory into which our (temp) PDF->bitmap will go
    os.makedirs("scanPNGs/submittedHomework", exist_ok=True)
    # finally a directory into which pageImages go
    os.makedirs("decodedPages/submittedHomework", exist_ok=True)

    from plom.scan import scansToImages

    subs = defaultdict(list)
    for fn in glob.glob("submittedHomework/*.pdf"):
        # record who did what
        sid, q = extractIDQ(fn)
        subs[sid].append(q)
        print("Processing PDF {} to images".format(fn))
        scansToImages.processScans(fn, homework=True)


def uploadHWImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer

    # make directories for upload
    os.makedirs("sentPages", exist_ok=True)

    print("Upload hw images to server")
    sendPagesToServer.uploadHWPages(server, password)


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

for x in (spU, spS, spC):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "submitted":
        whoDidWhat()
    elif args.command == "process":
        processScans()
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
