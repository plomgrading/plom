#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

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
import time
import argparse
from warnings import warn

from plom import __version__
from plom import Default_Port


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

    # Start server into background
    serverproc = subprocess.Popen(split("plom-server launch"))
    time.sleep(1.0)
    try:
        serverproc.wait(1.0)
    except subprocess.TimeoutExpired:
        pass
    else:
        r = serverproc.returncode
        print("Server has prematurely stopped with return code {}".format(r))
        # TODO: server could send specific return code for "address already in use"?
        msg = "Server didn't start.  Is one already running?  See errors above."
        # raise RuntimeError(msg) from None
        print(msg)
        exit(r)

    assert serverproc.returncode is None, "has the server died?"

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

    time.sleep(0.5)
    try:
        serverproc.wait(0.5)
    except subprocess.TimeoutExpired:
        pass
    else:
        r = serverproc.returncode
        print("Server has prematurely stopped with return code {}".format(r))
        msg = "Server may have unexpectedly died during uploading.  See errors above."
        print(msg)
        exit(r)

    print('\n*** Now run "plom-client" ***\n')
    print("  * Server currently running under PID " + str(serverproc.pid) + "\n")
    # TODO: output account info directly, perhaps just "user*"?
    print('  * See "serverConfiguration/userListRaw.csv" for account info\n')
    print("  * Press Ctrl-C to stop this demo")
    serverproc.wait()


if __name__ == "__main__":
    main()
