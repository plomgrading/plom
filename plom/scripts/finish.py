#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom script for post-grading tasks.

NOTE: For now, most of these tasks must be run on the server, and
in the server's directory (where you ran `plom-server launch`).
This will change.
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


parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="command")

spCheck = sub.add_parser("check_completed",
    help="how's progress?",
    description="List progress and which tests that have been completed."
)
spClear = sub.add_parser(
    "clear",
    help='Clear "manager" manager',
    description='Clear "manager" login after a crash or other expected event.',
)
for x in (spCheck, spClear):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "manager" user')


def main():
    args = parser.parse_args()

    if args.command == "check_completed":
        plom.finish.check_completed.main(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()
    exit(0)


if __name__ == "__main__":
    main()
