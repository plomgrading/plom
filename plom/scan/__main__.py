#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao
# Copyright (C) 2023 Julian Lapenna

"""Plom tools for scanning tests and pushing to servers.

See help for each subcommand or consult online documentation for an
overview of the steps in setting up a server.

Most subcommands communicate with a server, which can be specified
on the command line or by setting environment variables PLOM_SERVER
and PLOM_MANAGER_PASSWORD.

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

  4. Run "plom-scan status" to get a summary of scanning to date.

  5. If something goes wrong such as crashes or interruptions, you may
     need to clear the "scanner" login with the `clear` command.

  These steps may be repeated as new PDF files come in: it is not
  necessary to wait until scanning is complete to start processing and
  uploading.
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path

from stdiomask import getpass

from plom.scan import __version__
from plom import Default_Port
from plom.scan import clear_login
from plom.scan import check_and_print_scan_status
from plom.scan import processScans, uploadImages


def get_parser():
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
        description="""
            Get scanning status report from server.
            You can customize the report using the switches below
            or omit all switches to get the full report.
        """,
    )
    spS.add_argument("--papers", action="store_true", help="show paper info")
    spS.add_argument("--unknowns", action="store_true", help="Show info about unknowns")
    spS.add_argument("--bundles", action="store_true", help="Show bundle info")

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
            Has not been extensively tested recently: NOT recommended.
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
            We recommend this option if you scanned the papers yourself.
            If a PDF page seems to contain exactly one bitmap image and
            nothing else, then extract that losslessly instead of rendering
            the page as a new PNG file.  This will be MUCH FASTER and will
            typically give nicer images for the common case where pages are
            simply JPEG/PNG images embedded in a PDF file.  But some care
            must be taken that the image is not annotated in any way and
            that no other markings appear on the page.
            If the papers were produced by other people, this option is NOT
            RECOMMENDED, in case it misses markings made on top of a bitmap
            base (e.g., from annotation software).
            For this reason, it is not yet the default.
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
    g.add_argument(
        "--demo",
        action="store_true",
        help="""
            Simulate scanning with random rotations, adding noise etc.
            Obviously not intended for production use.
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
        help="""
            Upload "collisions", pages which appear to already be on the server.
            You should not need this option except under exceptional circumstances.
        """,
    )
    spU.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="""
            Assume yes to any prompts (skipping --collisions prompts for
            confirmation).
        """,
    )
    for x in (spU, spS, spC, spP):
        x.add_argument(
            "-s",
            "--server",
            metavar="SERVER[:PORT]",
            action="store",
            help=f"""
                Which server to contact, port defaults to {Default_Port}.
                Also checks the environment variable PLOM_SERVER if omitted.
            """,
        )
        x.add_argument(
            "-w",
            "--password",
            type=str,
            help="""
                for the "scanner" user', also checks the
                environment variable PLOM_SCAN_PASSWORD.
            """,
        )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "server"):
        args.server = args.server or os.environ.get("PLOM_SERVER")

    if hasattr(args, "password"):
        args.password = args.password or os.environ.get("PLOM_SCAN_PASSWORD")

    if hasattr(args, "password") and not args.password:
        args.password = getpass('Please enter the "scanner" password: ')

    if args.command == "process":
        scan_pdf = args.scanPDF
        assert " " not in Path(scan_pdf).name, "File name should not have spaces"
        processScans(
            scan_pdf,
            gamma=args.gamma,
            extractbmp=args.extractbmp,
            demo=args.demo,
            msgr=(args.server, args.password),
        )
    elif args.command == "upload":
        bundle_name = args.bundleName
        assert " " not in bundle_name, "Bundle name should not have spaces"
        uploadImages(
            bundle_name,
            do_unknowns=args.unknowns,
            do_collisions=args.collisions,
            prompt=(not args.yes),
            msgr=(args.server, args.password),
        )
    elif args.command == "status":
        check_and_print_scan_status(
            args.papers,
            args.unknowns,
            args.bundles,
            msgr=(args.server, args.password),
        )
    elif args.command == "clear":
        clear_login(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
