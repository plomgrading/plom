#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

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

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path

from plom.scan import __version__
from plom.scan import clear_login
from plom.scan import check_and_print_scan_status
from plom.scan import processScans, uploadImages


def frontend(args):
    if args.command == "process":
        processScans(
            args.server,
            args.password,
            args.scanPDF,
            gamma=args.gamma,
            extractbmp=args.extractbmp,
        )
    elif args.command == "upload":
        uploadImages(
            args.server,
            args.password,
            args.bundleName,
            do_unknowns=args.unknowns,
            do_collisions=args.collisions,
        )
    elif args.command == "status":
        check_and_print_scan_status(args.server, args.password)
    elif args.command == "clear":
        clear_login(args.server, args.password)
    else:
        # parser.print_help()
        raise RuntimeError("Unexpected choice: report this as a bug!?")


def parse_the_user_args():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
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
    # TODO: maybe in the future?
    # spA = sub.add_parser(
    #     "all",
    #     help="Process, read and upload page images to scanner (WIP!)",
    #     description="Process, read and upload page images to scanner. CAUTION: Work in Progress!",
    # )
    # spA.add_argument("scanPDF", nargs="+", help="The PDF(s) containing scanned pages.")
    spP.add_argument("scanPDF", help="The PDF file of scanned pages.")
    g = spP.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "--gamma-shift",
        action="store_true",
        dest="gamma",
        help="""
            Apply white balancing to the scan, if the image format is
            lossless (PNG).
            By default, this gamma shift is NOT applied; this is because it
            may worsen some poor-quality scans with large shadow regions.
        """,
    )
    g.add_argument(
        "--no-gamma-shift",
        action="store_false",
        dest="gamma",
        help="Do not apply white balancing.",
    )
    g = spP.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "--extract-bitmaps",
        action="store_true",
        dest="extractbmp",
        help="""
            If a PDF page seems to contain exactly one bitmap image and
            nothing else, then extract that losslessly instead of rendering
            the page as a new PNG file.  This will typically give nicer
            images for the common scan case where pages are simply JPEG
            images.  But some care must be taken that the image is not
            annotated in any way and that no other markings appear on the
            page.
            As the algorithm to decide this is NOT YET IDEAL, this is
            currently OFF BY DEFAULT, but we anticipate it being the default
            in a future version.
        """,
    )
    g.add_argument(
        "--no-extract-bitmaps",
        action="store_false",
        dest="extractbmp",
        help="""
            Don't try to extract bitmaps; just render each page.  This is
            safer but not always ideal for image quality.
        """,
    )

    spU.add_argument("bundleName", help="Usually the name of the PDF file.")
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
    for x in (spU, spS, spC, spP):
        x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
        x.add_argument("-w", "--password", type=str, help='for the "scanner" user')

    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_SCAN_PASSWORD"]
        except KeyError:
            pass

    return args


def main():
    args = parse_the_user_args()
    frontend(args)


if __name__ == "__main__":
    main()