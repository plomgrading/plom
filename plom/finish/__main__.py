#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao

"""Plom script for post-grading tasks.

## Overview of the "finishing" process

  1. Use the `status` command to check on progress.

  2. Use the `csv` command to produce a CSV file summarizing
     completed papers and marks (so far, if marking is ongoing).

  3. Run the `reassemble` command build PDFs of marked papers.

  4. Run the `solutions` command to assemble individualised solution PDFs.

  5. Run the `audit` command to produce an audit of all files used.

## Digital return

The reassembled PDF files can be returned to students in various ways.
The `webpage` command builds a webpage with individualized secret codes
to be distributed to each student e.g., via Canvas or another LMS.
Running `webpage --solutions` includes solution return on that webpage.
"""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from textwrap import dedent

from stdiomask import getpass

from plom import __version__
from plom import Default_Port
from plom.finish import clear_manager_login
from plom.finish import CSVFilename
from plom.finish import pull_spreadsheet
from plom.finish import reassemble_paper, reassemble_all_papers
from plom.finish import assemble_solutions
from plom.finish import download_rubric_files
from plom.finish import audit
from plom.finish import make_coded_return_webpage
import plom.finish.check_completed
import plom.finish.reassemble_ID_only


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

    spCheck = sub.add_parser(
        "status",
        help="How's progress?",
        description="List progress and which tests that have been completed.",
    )
    spCSV = sub.add_parser(
        "csv",
        help="CSV file with marks/progress info",
        description='Create a spreadsheet of grades named "{}".'.format(CSVFilename),
        epilog="""
            If grading is not yet complete, the spreadsheet contains partial info
            and any warnings so far.
        """,
    )
    spAssemble = sub.add_parser(
        "reassemble",
        help="Create PDFs to return to students",
        description="""
            After papers have been ID'd and marked, this command builds PDFs
            to return to students.  A special case deals with the online-return
            of papers that were marked offline (before scanning).
        """,
    )
    spAssemble.add_argument(
        "testnum",
        type=int,
        nargs="?",
        help="""
            Which test number to reassemble or omit to reassemble all papers.
        """,
    )
    spAssemble.add_argument(
        "--skip-existing",
        action="store_true",
        help="""
            If a file already exists, don't rebuild it.  Careful: does not
            check if the file is out of date!  Thus turned off by default.
        """,
    )
    spAssemble.add_argument(
        "--ided_only",
        action="store_true",
        help="""
            Reassemble PDF files for ID'ed (but offline-graded) papers.
        """,
    )
    spCodedReturn = sub.add_parser(
        "webpage",
        help="Create HTML page for digital return",
        description="Prepare HTML page for return using out-of-band per-student secret codes.",
        epilog=dedent(
            """
            The webpage will be in `codedReturn` and the secret codes in
            `return_codes.csv`.

            There may be scripts in `share/plom/contrib` to assist with
            distributing the secret codes.

            This command must have access to the results of `reassemble`.
        """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    spCodedReturn.add_argument(
        "--solutions",
        action="store_true",
        help="""
            Add a 'get solutions' button to the return website.
        """,
    )
    spCodedReturn.add_argument(
        "--hex",
        action="store_true",
        help="""
            Use a string of hexadecimal instead of decimal digits for the
            secret codes.
            More secure but may cause problems if you use certain Canvas
            workarounds to distribute the codes.
        """,
    )
    spCodedReturn.add_argument(
        "--digits",
        type=int,
        default=9,
        metavar="N",
        action="store",
        help="Length of the secret code.  Defaults to 9.",
    )
    spCodedReturn.add_argument(
        "--salt",
        type=str,
        help="""
            Instead of random codes, use a hash of the student ID, salted
            with the string SALT.  The codes will then be reproducible by
            anyone who knows this string (and the student IDs).
            As its susceptible to offline attacks, a longer string is
            recommended: you can put quotes around a phrase e.g.,
            `--salt "Many a slip twixt the cup and the lip"`.
        """,
    )
    spSolution = sub.add_parser(
        "solutions",
        help="Create solution-PDFs to return to students",
        description="""
            If all solution images present, then this will build individualised
            solution PDFs for the students (based on the particular q/v of their
            test.
        """,
    )
    spSolution.add_argument(
        "-m",
        "--mark",
        action="store_true",
        help="""
            Watermark the solutions with the student number.
        """,
    )
    spSolution.add_argument(
        "testnum",
        type=int,
        nargs="?",
        help="""
            Build a solution for this particular test, or omit to reassemble
            solutions for all identified and marked papers.
        """,
    )
    spRubric = sub.add_parser(
        "rubric",
        help="Download rubric info",
        description="""
            Download list of rubrics as json and the test-rubric use matrix (indexed by test-number and rubric-key) also as json.
        """,
    )
    spAudit = sub.add_parser(
        "audit",
        help="Construct an audit of all image files used",
        description="""
        Download an audit of all files + bundles used. Saved as 'audit.json'.
        """,
    )
    spClear = sub.add_parser(
        "clear",
        help='Clear "manager" login',
        description='Clear "manager" login after a crash or other expected event.',
    )
    for x in (
        spCheck,
        spCSV,
        spAssemble,
        spClear,
        spSolution,
        spCodedReturn,
        spRubric,
        spAudit,
    ):
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
    for x in (spCheck, spCSV, spAssemble, spSolution, spRubric, spClear, spAudit):
        x.add_argument(
            "-w",
            "--password",
            type=str,
            help="""
                for the "manager" user, also checks the
                environment variable PLOM_MANAGER_PASSWORD.
            """,
        )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if hasattr(args, "server"):
        args.server = args.server or os.environ.get("PLOM_SERVER")

    if hasattr(args, "password"):
        args.password = args.password or os.environ.get("PLOM_MANAGER_PASSWORD")
        if not args.password:
            args.password = getpass('Please enter the "manager" password: ')

    # Note: some of these commands use exit() directly
    if args.command == "status":
        plom.finish.check_completed.main(args.server, args.password)
    elif args.command == "csv":
        pull_spreadsheet(msgr=(args.server, args.password))
    elif args.command == "reassemble":
        if args.ided_only:
            plom.finish.reassemble_ID_only.main(args.server, args.password)
        elif args.testnum:
            reassemble_paper(
                args.testnum, msgr=(args.server, args.password), skip=args.skip_existing
            )
        else:
            reassemble_all_papers(
                msgr=(args.server, args.password), skip=args.skip_existing
            )
    elif args.command == "solutions":
        assemble_solutions(
            testnum=args.testnum,
            msgr=(args.server, args.password),
            watermark=args.mark,
            verbose=True,
        )
    elif args.command == "webpage":
        make_coded_return_webpage(
            args.hex, args.digits, args.salt, args.server, args.solutions
        )
    elif args.command == "rubric":
        download_rubric_files(msgr=(args.server, args.password))
    elif args.command == "audit":
        audit(msgr=(args.server, args.password))

    elif args.command == "clear":
        clear_manager_login(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
