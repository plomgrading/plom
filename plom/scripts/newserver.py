#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

"""Command line tool to start Plom servers."""

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path
import subprocess

from plom import __version__


_default_src_location = Path("/src") / "plom_server"

server_instructions = f"""Overview of running the Plom server:

  The next-gen Django-based Plom server must be run inside its
  own source code.  This is hopefully only temporary (see
  Issue #2932, Issue #2759, and maybe others).

  If you are not using our container, then its very likely your
  source code is not in the default "{_default_src_location}"
  and you will need to configure with a command line argument.

  For example, if you are currently in the source code, try

    plom-new-server --src $PWD
"""


def get_parser():
    parser = argparse.ArgumentParser(
        epilog=server_instructions,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "--src",
        type=str,
        help=f"""
            Where the source code is located.
            Defaults to "{_default_src_location}".
            This is hopefully just a temporary hack
            and this argument will disappear without
            notice in a future version.
        """,
    )
    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    # TODO: see Issue #2932 and Issue #2759.

    if not args.src:
        args.src = _default_src_location
    print(f"Changing the working directory to {args.src}")
    os.chdir(args.src)

    subprocess.check_call("./docker_run.sh")


if __name__ == "__main__":
    main()
