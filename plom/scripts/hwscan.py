#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao

"""Plom tools for dealing with student self-submitted scans.

## Processing and uploading homework

There are two main approaches to uploading: Test Pages and Homework Pages.
This tool deals with "Homework Pages", self-scanned work typically
without QR-codes that are associated with a particular known student but
are unstructured or understructured in the their relationship to the exam
template.

If you instead are dealing with QR-coded pages where you may not yet know
which pages belong to which student, see ``plom-scan`` instead.

## Notes

Most uses of this tool require that your server has a classlist.
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from stdiomask import getpass

from plom import __version__
from plom import Default_Port
from plom.scan import clear_login
from plom.scan import print_who_submitted_what
from plom.scan import check_and_print_scan_status
from plom.scan import processHWScans, processMissing
from plom.scan import processAllHWByQ


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
    #
    spW = sub.add_parser(
        "submitted",
        help="status of student-submitted work, either local or on server",
        description="List student IDs and their submitted questions in the local"
        + " 'submittedHWByQ' directory or their work already uploaded the server.",
    )
    spP = sub.add_parser(
        "process",
        help="Process indicated PDF for one student and upload to server.",
        description="""
            Process a bundle of work (typically a PDF file) from one student.
            You must provide the student ID.  You must also indicate which
            question(s) is/are in this bundle.
            Various flags control other aspects of how the bundle is
            processed.
        """,
    )
    spA = sub.add_parser(
        "allbyq",
        help="Process and upload all PDFs in 'submittedHWByQ' directory and upload to server",
        description="""
            Process and upload all PDFs in 'submittedHWByQ' directory.
            Looks for student id and question number from the filename
            `foo_bar.12345678.q.pdf`.  Upload each to server.
        """,
    )
    spM = sub.add_parser(
        "missing",
        help="Replace missing answers with 'not submitted' pages.",
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
        help="Clear 'scanner' login",
        description="Clear 'scanner' login after a crash or other expected event.",
    )
    #

    spW.add_argument(
        "-d",
        "--directory",
        action="store_true",
        help="Check submissions in local directory and not on server.",
    )

    spP.add_argument("hwPDF", action="store", help="PDF containing homework")
    spP.add_argument("studentid", action="store", help="Student ID")
    spP.add_argument(
        "--bundle-name",
        action="store",
        metavar="NAME",
        help="""
            Override the default bundle name instead of generating it from
            the PDF file name.
            Note Plom uses both the bundle name and the "md5sum" of the
            PDF file to detect possible duplicate uploads.
        """,
    )
    spP.add_argument(
        "-q",
        "--question",
        metavar="N",
        help="""
            Which question(s) are answered in file.
            You can pass a single integer, or a list like `-q [1,2,3]`
            which uploads each page to questions 1, 2 and 3.
            You can also pass the special string `-q all` which uploads
            each page to all questions.
            If you need to specify questions per page, you can pass a list
            of lists: each list gives the questions for each page.
            For example, `-q [[1],[2],[2],[2],[3]]` would upload page 1 to
            question 1, pages 2-4 to question 2 and page 5 to question 3.
            A common case is `-q [[1],[2],[3]]` to upload one page per
            question.
        """,
    )
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
            Also, it may undo actions to make files unique via metadata which
            can cause problems with self-scanned work.
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

    spA.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Answer yes to prompts.",
    )
    spM.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Answer yes to prompts.",
    )

    for x in (spW, spP, spA, spS, spC, spM):
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

    if args.command == "submitted":
        print_who_submitted_what(args.directory, msgr=(args.server, args.password))
    elif args.command == "process":
        processHWScans(
            args.hwPDF,
            args.studentid,
            args.question,
            gamma=args.gamma,
            extractbmp=args.extractbmp,
            bundle_name=args.bundle_name,
            msgr=(args.server, args.password),
        )
    elif args.command == "allbyq":
        # TODO: gamma and extractbmp?
        processAllHWByQ(args.server, args.password, args.yes)
    elif args.command == "missing":
        processMissing(yes_flag=args.yes, msgr=(args.server, args.password))
    elif args.command == "status":
        check_and_print_scan_status(
            args.papers, args.unknowns, args.bundles, msgr=(args.server, args.password)
        )
    elif args.command == "clear":
        clear_login(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
