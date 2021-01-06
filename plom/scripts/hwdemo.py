#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom script to start a demo server for homework submissions.

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


parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)


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

    subprocess.check_call(split("plom-build new --demo"))
    subprocess.check_call(split("plom-server init"))
    subprocess.check_call(split("plom-server users --demo"))

    # Start server into background
    print("Running server I hope")
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

    print("Server seems to be running, so we move on to uploading")

    subprocess.check_call(split("plom-build class --demo -w 1234"))
    subprocess.check_call(split("plom-build make -w 1234"))
    # this creates two batches of fake hw - prefixes = hwA and hwB
    subprocess.check_call(split("plom-fake-hwscribbles -w 1234"))

    print("Processing some individually")
    # TODO: this is fragile, should not hardcode these student numbers!
    subprocess.check_call(
        split(
            "plom-hwscan process submittedHWByQ/semiloose.11015491._.pdf 11015491 -q 1,2,3 -w 4567"
        )
    )
    subprocess.check_call(
        split(
            "plom-hwscan process submittedHWByQ/semiloose.11135153._.pdf 11135153 -q 1,2,3 -w 4567"
        )
    )

    print("Processing all hw by question submissions.")
    subprocess.check_call(split("plom-hwscan allbyq -w 4567 -y"))
    print("Replacing all missing questions.")
    subprocess.check_call(split("plom-hwscan missing -w 4567 -y"))
    # print(">> TODO << process loose pages")

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
    # TODO: output account info directly, perhaps just "user*"?
    print('  * See "serverConfiguration/userListRaw.csv" for account info\n')
    print("  * Press Ctrl-C to stop this demo")
    serverproc.wait()


if __name__ == "__main__":
    main()
