#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom script for post-grading tasks.

## Overview of the "finishing" process

  1. Use the `check_completed` command to check on progress.

  2. Use the `spreadsheet` command to produce a CSV file summarizing
     completed papers and marks (so far, if marking is ongoing).

  3. Run the `reassemble` command build PDFs of marked papers.


## Digital return

The reassembled PDF files can be returned to students in various ways.
Plom currently includes tools to upload to a webpage (with a secret code
distributed to students via Canvas).  See contents of the `plom.finish`
module for now---we anticipate these tools to mature in future releases.
"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import os
import shutil

# TODO: be more decisive about how this should be
from plom.finish.clearLogin import clearLogin
import plom.finish.check_completed
import plom.finish.spreadsheet
from plom.finish.spreadsheet import CSVFilename
import plom.finish.reassemble_completed
import plom.finish.reassemble_ID_only


parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="command")

spCheck = sub.add_parser(
    "check_completed",
    help="how's progress?",
    description="List progress and which tests that have been completed.",
)
spCSV = sub.add_parser(
    "spreadsheet",
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
    epilog="""
        WARNING: This command must be run on the server, and in the
        server's directory (where you ran `plom-server launch`).
        This may change in the future.
    """,
)
spAssemble.add_argument(
    "--totalled_only",
    action="store_true",
    help="Reassemble PDF files for ID and totalled (but offline-graded) papers.",
)

spClear = sub.add_parser(
    "clear",
    help='Clear "manager" login',
    description='Clear "manager" login after a crash or other expected event.',
)
for x in (spCheck, spCSV, spAssemble, spClear):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "manager" user')


def main():
    args = parser.parse_args()

    if args.command == "check_completed":
        plom.finish.check_completed.main(args.server, args.password)
    elif args.command == "spreadsheet":
        plom.finish.spreadsheet.main(args.server, args.password)
    elif args.command == "reassemble":
        if args.totalled_only:
            plom.finish.reassemble_ID_only.main(args.server, args.password)
        else:
            plom.finish.reassemble_completed.main(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()
    exit(0)


if __name__ == "__main__":
    main()
