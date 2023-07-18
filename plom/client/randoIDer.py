#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Elizabeth Xiao

"""Randomly ID papers for testing purposes."""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import sys

from stdiomask import getpass

from plom import Default_Port
from .random_identifying_utils import do_rando_identifying

__all__ = [
    "do_rando_identifying",
]


def get_parser():
    parser = argparse.ArgumentParser(
        description="Perform identifier tasks randomly, generally for testing."
    )

    parser.add_argument(
        "-w",
        "--password",
        type=str,
        help="""
            by default, for the "scanner" user', also checks the
            environment variable PLOM_SCAN_PASSWORD.
        """,
    )
    parser.add_argument("-u", "--user", help='Override default of "scanner"')
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help=f"""
            Which server to contact, port defaults to {Default_Port}.
            Also checks the environment variable PLOM_SERVER if omitted.
        """,
    )
    return parser


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    args.server = args.server or os.environ.get("PLOM_SERVER")

    if not args.user:
        args.user = "scanner"

    if args.user == "scanner":
        args.password = args.password or os.environ.get("PLOM_SCAN_PASSWORD")

    if not args.password:
        args.password = getpass(f"Please enter the '{args.user}' password: ")

    sys.exit(do_rando_identifying(args.server, args.user, args.password))
