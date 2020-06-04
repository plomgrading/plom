#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning tests and pushing to servers.

## Overview of the scanning process

  1. Decide on a working directory for your scans, copy your PDFs into
     that directory and then cd into it.

  2. Use the `process` command to split your PDF into bitmaps of each page.

  3. Ensure the Plom server is running and a password for the "scanner"
     user has been set.

  4. Use the `read` command to read QR codes from the pages and match
     these against expectations from the server.

  5. Use the `upload` command to send pages to the server.  There are
     additional flags for dealing with special cases:

       a. Pages that could not be identified are called "Unknowns".
          They can include "Extra Pages" without QR codes, poor-quality
          scans where the QR reader failed, folded papers, etc.  A small
          number is normal but large numbers are cause for concern and
          sanity checking.  A human will (eventually) have to identify
          these manually.

       b. If the system detects you trying to upload a test page
          corresponding to one already in the system (but not identical)
          then those pages are filed as "Collisions". If you have good
          paper-handling protocols then this should not happen, except
          in exceptional circumstances (such as rescanning an illegible
          page).  Force the upload these if you really need to; the
          manager will then have to look at them.

  6. Run "plom-scan status" to get a brief summary of scanning to date.

  7. If something goes wrong such as crashes or interruptions, you may
     need to clear the "scanner" login with the `clear` command.
"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import shutil

from plom import __version__


# TODO: this bit of code from messenger could be useful here
#    if os.path.isfile("server.toml"):
#        with open("server.toml") as fh:
#            si = toml.load(fh)
#        server = si["server"]
#        if server and ":" in server:
#            server, message_port = server.split(":")


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def processScans(PDFs):
    from plom.scan import scansToImages

    # make PDF archive directory
    os.makedirs("archivedPDFs", exist_ok=True)
    # make a directory into which our (temp) PDF->bitmap will go
    os.makedirs("scanPNGs", exist_ok=True)
    # finally a directory into which pageImages go
    os.makedirs("pageImages", exist_ok=True)

    # first check that we can find all the files
    for fname in PDFs:
        if not os.path.isfile(fname):
            print("Cannot find file {} - skipping".format(fname))
            continue
        print("Processing PDF {} to images".format(fname))
        scansToImages.processScans(fname)


def readImages(server, password):
    from plom.scan import readQRCodes

    # make decodedPages and unknownPages directories
    os.makedirs("decodedPages", exist_ok=True)
    os.makedirs("unknownPages", exist_ok=True)
    readQRCodes.processBitmaps(server, password)

def uploadImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer

    # make directories for upload
    os.makedirs("sentPages", exist_ok=True)
    os.makedirs("discardedPages", exist_ok=True)
    os.makedirs("collidingPages", exist_ok=True)

    print("Upload images to server")
    [TPN, updates] = sendPagesToServer.uploadPages(server, password)
    print("Tests were uploaded to the following studentIDs: {}".format(TPN.keys()))
    print("Server reports {} papers updated.".format(updates))

    if unknowns:
        print(">> TO DO FIX <<")
        # from plom.scan import sendUnknownsToServer
        # print("Also upload unknowns")
        # os.makedirs("sentPages/unknowns", exist_ok=True)
        # [SIDQ, updates] = sendUnknownsToServer.uploadUnknowns(server, password)
    if collisions:
        print(">> TO DO FIX <<")
        # from plom.scan import sendCollisionsToServer
        # print("Also collisions unknowns")
        # os.makedirs("sentPages/collisions", exist_ok=True)
        # sendCollisionsToServer.uploadCollisions(server, password)


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command", description="Tools for dealing with scans.")
#
spP = sub.add_parser("process", help="Process scanned PDFs to images.")
spR = sub.add_parser("read", help="Read QR-codes from images and collate.")
spU = sub.add_parser("upload", help="Upload page images to scanner")
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser(
    "clear",
    help="Clear 'scanner' login",
    description="Clear 'scanner' login after a crash or other expected event.",
)
#
spP.add_argument("scanPDF", nargs="+", help="The PDF(s) containing scanned pages.")
spU.add_argument(
    "-u",
    "--unknowns",
    action="store_true",
    help="Upload 'unknowns'. Unknowns are pages from which the QR-codes could not be read.",
)
spU.add_argument(
    "-c",
    "--collisions",
    action="store_true",
    help="Upload 'collisions'. Collisions are pages which appear to be already on the server. You should not need this option except under exceptional circumstances.",
)
for x in (spR, spU, spS, spC):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "process":
        processScans(args.scanPDF)
    elif args.command == "read":
        readImages(args.server, args.password)
    elif args.command == "upload":
        uploadImages(args.server, args.password, args.unknowns, args.collisions)
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()
    exit(0)


if __name__ == "__main__":
    main()
