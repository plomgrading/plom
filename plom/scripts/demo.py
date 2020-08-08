#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Victoria Schuster

"""Plom script to start a demo server.

Instructions:
  * Make a new directory
  * Run this script inside it
  * In a new terminal, run the Plom Client and connect to localhost.
"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import os
import subprocess
from shlex import split
import argparse
from warnings import warn
from pathlib import Path

from plom import __version__
from plom import Default_Port
from plom.server import PlomServer


parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
parser.add_argument(
    "-n",
    "--num-papers",
    type=int,
    # default=20,  # we want it to give None
    metavar="N",
    help="How many fake exam papers for the demo (defaults to 20 if omitted)",
)
parser.add_argument(
    "--port",
    type=int,
    help=f"Which port to use for the demo server ({Default_Port} if omitted)",
)


def main():
    args = parser.parse_args()
    print("Plom version {}".format(__version__))

    buildDirectory()

    if len(os.listdir(os.getcwd())) != 0:
        print('We recommend calling "{}" in an empty folder!'.format(parser.prog))
        warn("Current directory not empty")
    for f in (
        "specAndDatabase",
        "serverConfiguration",
        "archivedPDFs",
        "pageImages",
        "scanPNGs",
        "pages",
    ):
        if os.path.exists(f):
            raise RuntimeError('Directory "{}" must not exist for this demo.'.format(f))

    if args.port:
        subprocess.check_call(split(f"plom-server init --port {args.port}"))
    else:
        subprocess.check_call(split("plom-server init"))
    subprocess.check_call(split("plom-server users --demo"))

    if args.num_papers:
        subprocess.check_call(
            split("plom-build new --demo --demo-num-papers {}".format(args.num_papers))
        )
    else:
        subprocess.check_call(split("plom-build new --demo"))

    background_server = PlomServer(basedir=".")

    assert background_server.process_is_running(), "has the server died?"
    assert background_server.ping_server(), "cannot ping server, something gone wrong?"
    print("Server seems to be running, so we move on to building tests and uploading")

    if args.port:
        server = f"localhost:{args.port}"
    else:
        server = "localhost"
    subprocess.check_call(split(f"plom-build class --demo -w 1234 -s {server}"))
    subprocess.check_call(split(f"plom-build rubric --demo -w 1234 -s {server}"))
    subprocess.check_call(split(f"plom-build make -w 1234 -s {server}"))
    subprocess.check_call(split(f"plom-fake-scribbles -w 1234 -s {server}"))

    # TODO:
    # subprocess.check_call(
    #     split(
    #         f"plom-scan all -w 4567 -s {server} fake_scribbled_exams1.pdf fake_scribbled_exams2.pdf fake_scribbled_exams3.pdf"
    #     )
    # )

    opts = "--no-gamma-shift"
    # opts = ""
    for f in (
        "fake_scribbled_exams1",
        "fake_scribbled_exams2",
        "fake_scribbled_exams3",
    ):
        subprocess.check_call(
            split(f"plom-scan process -w 4567 -s {server} {opts} {f}.pdf")
        )
        subprocess.check_call(split(f"plom-scan upload -w 4567 -s {server} -u {f}"))

    assert background_server.process_is_running(), "has the server died?"
    assert background_server.ping_server(), "cannot ping server, something gone wrong?"
    print("Server seems to still be running: demo setup is complete")

    print('\n*** Now run "plom-client" ***\n')
    print(f"  * Server currently running under PID {background_server.pid}\n")
    # TODO: output account info directly, perhaps just "user*"?
    print('  * See "userListRaw.csv" for account info\n')
    # print("  * Press Ctrl-C to stop this demo")
    # background_server.wait()
    input("Press enter when you want to stop the server...")
    background_server.stop()
    print("Server stopped, goodbye!")


def buildDirectory():
    current_path = Path(os.getcwd())
    path = current_path / "Plom_Demo"

    n = 0
    while path.exists():
        print('"{}" already exists: generating a new name...'.format(path))
        n = n + 1
        path = current_path / "Plom_Demo{}".format(n)

    try:
        os.mkdir(path)
    except OSError:
        print("Creation of the directory %s failed" % path)
    else:
        print('Created the directory "{}" for the demo'.format(path))

    try:
        # Change the current working Directory
        os.chdir(path)
        print('Directory changed, files can be found at "{}"'.format(path))
    except OSError:
        print("Can't change the Current Working Directory")


if __name__ == "__main__":
    main()
