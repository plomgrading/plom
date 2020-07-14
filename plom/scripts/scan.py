#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning tests and pushing to servers.

## Overview of the scanning process

  1. Decide on a working directory for your scans, copy your PDFs into
     that directory and then cd into it.

  2. Use the `process` command to split your first PDF into bitmaps of
     each page.  This will also read any QR codes from the pages and
     match these against expectations from the server.

  3. Use the `upload` command to send pages to the server.  There are
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

  4. Run "plom-scan status" to get a brief summary of scanning to date.

  5. If something goes wrong such as crashes or interruptions, you may
     need to clear the "scanner" login with the `clear` command.

  These steps may be repeated as new PDF files come in: it is not
  necessary to wait until scanning is complete to start processing and
  uploading.
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


def make_required_directories():
    # we need
    directory_list = [
        "archivedPDFs",
        "bundles",
        "uploads/sentPages",
        "uploads/discardedPages",
        "uploads/collidingPages",
        "uploads/sentPages/unknowns",
        "uploads/sentPages/collisions",
    ]
    for dir in directory_list:
        os.makedirs(dir, exist_ok=True)


def processScans(server, password, pdf_fname):
    """Process PDF file into images."""
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer

    make_required_directories()

    if not os.path.isfile(pdf_fname):
        print("Cannot find file {} - skipping".format(pdf_fname))
        return
    print("Declaring bundle PDF {} to server".format(pdf_fname))
    rval = sendPagesToServer.declareBundle(pdf_fname, server, password)
    # should be [True, name] or [False, name] [False,md5sum]
    # or [False, both, name, [all the files already uploaded]]
    if rval[0] is True:
        bundle_name = rval[1]
        skip_list = []
    else:
        if rval[1] == "name":
            print(
                "The bundle name {} has been used previously for a different bundle. Stopping".format(
                    pdf_fname
                )
            )
            return
        elif rval[1] == "md5sum":
            print(
                "A bundle with matching md5sum is already in system with a different name. Stopping".format(
                    pdf_fname
                )
            )
            return
        elif rval[1] == "both":
            print(
                "Warning - bundle {} has been declared previously - you are likely trying again as a result of a crash. Continuing".format(
                    pdf_fname
                )
            )
            bundle_name = rval[2]
            skip_list = rval[3]
        else:
            print("Should not be here!")
            exit(1)

        print("Processing PDF {} to images".format(pdf_fname))
    scansToImages.processScans([pdf_fname])


def readImages(server, password):
    from plom.scan import readQRCodes

    readQRCodes.processBitmaps(server, password)


def uploadImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer, scansToImages

    print("Upload images to server")
    [TPN, updates] = sendPagesToServer.uploadTPages(server, password)
    print("Tests were uploaded to the following studentIDs: {}".format(TPN.keys()))
    print("Server reports {} papers updated.".format(updates))

    if unknowns:
        from plom.scan import sendUnknownsToServer

        print("Also upload unknowns")
        sendUnknownsToServer.uploadUnknowns(server, password)
    if collisions:
        print(">> TO DO FIX <<")
        # from plom.scan import sendCollisionsToServer
        # print("Also collisions unknowns")
        # sendCollisionsToServer.uploadCollisions(server, password)


def doAllToScans(server, password, scanPDFs):
    from plom.scan import scansToImages, sendPagesToServer, readQRCodes

    make_required_directories()

    # do all steps for one PDF at a time.
    for fname in scanPDFs:
        if not os.path.isfile(fname):
            print("Cannot find file {} - skipping".format(fname))
            continue
        print("Declaring bundle PDF {} to server".format(fname))
        rval = sendPagesToServer.declareBundle(fname, server, password)
        if rval[0] is False:
            if rval[1] == "name":
                print(
                    "The bundle name {} has been used previously. Stopping".format(
                        fname
                    )
                )
            elif rval[1] == "md5sum":
                print(
                    "A bundle with matching md5sum is already in system. Stopping".format(
                        fname
                    )
                )
            else:
                print("Should not be here!")
            exit(1)

        print("Processing PDF {} to images".format(fname))
        scansToImages.processScans([fname])
        readQRCodes.processBitmaps(server, password)
        [TPN, updates] = sendPagesToServer.uploadTPages(server, password)
        print("Tests were uploaded to the following studentIDs: {}".format(TPN.keys()))
        print("Server reports {} papers updated.".format(updates))
        # now archive that pdf.
        scansToImages.archiveTBundle(fname)


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command")

spP = sub.add_parser(
    "process",
    help="Process scanned PDF to images and read QRs",
    description="Process one scanned PDF into page images, read QR codes and check info with server (e.g., versions match).",
)
spU = sub.add_parser(
    "upload",
    help="Upload page images to scanner",
    description="Upload page images to scanner.",
)
spS = sub.add_parser(
    "status",
    help="Get scanning status report from server",
    description="Get scanning status report from server.",
)
spC = sub.add_parser(
    "clear",
    help='Clear "scanner" login',
    description='Clear "scanner" login after a crash or other expected event.',
)
spA = sub.add_parser(
    "all",
    help="Process, read and upload page images to scanner (WIP!)",
    description="Process, read and upload page images to scanner. CAUTION: Work in Progress!",
)
spP.add_argument("scanPDF", help="The PDF file of scanned pages.")
spU.add_argument(
    "-u",
    "--unknowns",
    action="store_true",
    help='Upload "unknowns", pages from which the QR-codes could not be read.',
)
spU.add_argument(
    "-c",
    "--collisions",
    action="store_true",
    help='Upload "collisions", pages which appear to already be on the server. '
    + "You should not need this option except under exceptional circumstances.",
)
spA.add_argument("scanPDF", nargs="+", help="The PDF(s) containing scanned pages.")
#
for x in (spU, spS, spC, spP, spA):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "process":
        processScans(args.server, args.password, args.scanPDF)
        readImages(args.server, args.password)
    elif args.command == "upload":
        uploadImages(args.server, args.password, args.unknowns, args.collisions)
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    elif args.command == "all":
        doAllToScans(args.server, args.password, args.scanPDF)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
