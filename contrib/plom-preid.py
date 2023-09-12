#!/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Colin B. Macdonald

"""Pre-ID individual papers on a Plom Server

This can be used for "just-in-time" paper assignments, in conjunction
with `plom-hwscan`.

You need to set appropriate environment variables, so that this
will work:

    server = os.environ.get("PLOM_SERVER")
    pwd = os.environ.get("PLOM_MANAGER_PASSWORD")

You can try against the built-in demo like:

    plom-preid --papernum 17 --sid 12576612

which should assign paper number 17 to Colston, Jennifer.
"""

import argparse
import os
from pathlib import Path

from plom import __version__ as __plom_version__
from plom.plom_exceptions import PlomServerNotReady

from plom.create import start_messenger

# from plom.scan import start_messenger


__script_version__ = "0.0.1"


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__script_version__} (using Plom version {__plom_version__}, ",
    )
    parser.add_argument(
        "--sid",
        type=str,
        action="store",
        help="""
        Specify a UBC student ID, 8-digits.
        """,
    )
    parser.add_argument(
        "--papernum",
        type=str,
        action="store",
        help="""
            What test number to assign.  Must be unused, not sure what
            happens if its in-use...  Be careful.
        """,
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    server = os.environ.get("PLOM_SERVER")
    pwd = os.environ.get("PLOM_MANAGER_PASSWORD")
    # pwd = os.environ.get("PLOM_SCAN_PASSWORD")
    # pwd = os.environ.get("PLOM_PASSWORD")
    # user = os.environ.get("PLOM_USER")

    msgr = start_messenger(server, pwd)

    try:
        # Debugging: this one lives in ScanMessenger: need to swap some stuff above
        # N = msgr.sidToTest(sid)
        # print(N)
        # print(type(N))

        # push the student ID to the prediction-table in the database
        msgr.pre_id_paper(args.papernum, args.sid, predictor="prename")
        # can check if it worked in Manager -> Progress -> ID Progress -> table on right

    finally:
        msgr.closeUser()
        msgr.stop()


if __name__ == "__main__":
    main()
