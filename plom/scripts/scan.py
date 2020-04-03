#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom tools for scanning tests and pushing to servers."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import os
import shutil


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
    # make a directory into which our (temp) PDF->PNG will go
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
    readQRCodes.processPNGs(server, password)


def uploadImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer

    # make directories for upload
    os.makedirs("sentPages", exist_ok=True)
    os.makedirs("discardedPages", exist_ok=True)
    os.makedirs("collidingPages", exist_ok=True)

    print("Upload images to server")
    sendPagesToServer.uploadPages(server, password)
    if unknowns:
        from plom.scan import sendUnknownsToServer

        print("Also upload unknowns")
        os.makedirs("sentPages/unknowns", exist_ok=True)
        sendUnknownsToServer.uploadUnknowns(server, password)
    if collisions:
        from plom.scan import sendCollisionsToServer

        print("Also collisions unknowns")
        os.makedirs("sentPages/collisions", exist_ok=True)
        sendCollisionsToServer.uploadCollisions(server, password)


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest="command", description="Tools for dealing with scans.")
#
spP = sub.add_parser("process", help="Process scanned PDFs to images.")
spR = sub.add_parser("read", help="Read QR-codes from images and collate.")
spU = sub.add_parser("upload", help="Upload page images to scanner")
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser("clear", help="Clear 'scanner' login", description="Clear 'scanner' login after a crash or other expected event.")
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
        print("\n>> Processing and uploading scans <<")
        print(
            "0. Decide on a working directory for your scans, copy your PDFs into that directory and then cd into it."
        )
        print(
            "1. Run 'plom-scan process <filename>' - this processes your PDF <filename> into PNGs of each page."
        )
        print(
            """2. NOT IMPLEMENTED YET, BUT COMING SOON - Optionally create a \"server.toml\" text file containing a single line with the server name and port such as:
    server = "localhost:1234"
    server = "plom.foo.bar:41982" """
        )
        print(
            "3. Make sure the newserver is running and that the password for the 'scanner' user has been set."
        )
        print(
            "4. Run 'plom-scan read' - this reads barcodes from the pages and files them away accordingly"
        )
        print('5. Run "plom-scan upload" to send identified pages to the server.')
        print(
            '6. Pages that could not be identified are called "Unknowns". In that case run "plom-scan upload -u" to send those unknowns to the server. The manager can then identify them manually.'
        )
        print(
            '7. If the system detects you trying to upload a test page corresponding to one already in the system (but not identical) then those pages are filed as "Collisions". If you have good paper-handling protocols then this should not happen. If you really do need to upload them to the system (the manager can look at them and decide) then run "plom-scan upload -c"'
        )
        print('8. Run "plom-scan status" to get a brief summary of scanning to date.')
        print(
            '9. If anything goes wrong and plom-scan crashes or is interupted, you might need to clear the "scanner" login from the server. To do this run "plom-scan clear"'
        )

    exit(0)


if __name__ == "__main__":
    main()
