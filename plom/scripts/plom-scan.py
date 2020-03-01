#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
sub = parser.add_subparsers(help="sub-command help", dest="command")
#
spP = sub.add_parser("process", help="Process scanned PDFs to images.")
spR = sub.add_parser("read", help="Read QR-codes from images and collate.")
spU = sub.add_parser("upload", help="Upload page images to scanner")
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser("clear", help="Clear 'scanner' login.")
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
# server + password stuff
parser.add_argument(
    "-w",
    "--password",
    type=str,
    help='Password of "scanner". Not needed for "process" subcommand',
)
parser.add_argument(
    "-s",
    "--server",
    metavar="SERVER[:PORT]",
    action="store",
    help='Which server to contact. Not needed for "process" subcommand',
)
# Now parse things
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
