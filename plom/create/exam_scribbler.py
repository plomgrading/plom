# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

"""Plom tool for scribbling fake answers on PDF files.

After the exam PDF files have been generated, this can be used to
scribble on them to simulate random student work.
"""

__copyright__ = "Copyright (C) 2019-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os

from stdiomask import getpass

from plom import __version__
from plom import Default_Port
from plom.create import make_scribbles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
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
    parser.add_argument(
        "-w",
        "--password",
        type=str,
        help="""
            for the "manager" user, also checks the
            environment variable PLOM_MANAGER_PASSWORD.
        """,
    )
    args = parser.parse_args()

    args.server = args.server or os.environ.get("PLOM_SERVER")
    args.password = args.password or os.environ.get("PLOM_MANAGER_PASSWORD")

    if not args.password:
        args.password = getpass('Please enter the "manager" password: ')

    make_scribbles(msgr=(args.server, args.password))


if __name__ == "__main__":
    main()
