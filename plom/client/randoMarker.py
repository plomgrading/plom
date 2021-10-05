#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2021 Elizabeth Xiao

"""Randomly scribble on papers to mark them for testing purposes.

This is a very very cut-down version of Annotator, used to
automate some random marking of papers.
"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import sys

from stdiomask import getpass

from .random_marking_utils import do_rando_marking


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform marking tasks randomly, generally for testing."
    )

    parser.add_argument("-w", "--password")
    parser.add_argument("-u", "--user", help='Override default of "scanner"')
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help="Which server to contact.",
    )
    args = parser.parse_args()

    args.server = args.server or os.environ.get("PLOM_SERVER")

    if not args.user:
        args.user = "scanner"

    if args.user == "scanner":
        args.password = args.password or os.environ.get("PLOM_SCAN_PASSWORD")

    if not args.password:
        args.password = getpass(f"Please enter the '{args.user}' password: ")

    sys.exit(do_rando_marking(args.server, args.user, args.password))
