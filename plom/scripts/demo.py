#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom script to start a demo server.

Instructions:
  * Make a new directory
  * Run this script inside it
  * In a new terminal, run the Plom Client and connect to localhost.
"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess
from shlex import split
import time
import argparse

from plom import version


parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
)


def main():
    args = parser.parse_args()
    print("Plom version {}".format(version.__version__))

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
    subprocess.check_call(split("plom-build make"))
    subprocess.check_call(split("plom-build class --demo"))
    subprocess.check_call(split("plom-fake-scribbles"))
    subprocess.check_call(split("plom-server init"))
    subprocess.check_call(split("plom-server users --demo"))

    # Start server into background
    serverproc = subprocess.Popen(split("plom-server launch"))
    time.sleep(1.0)

    subprocess.check_call(split("plom-scan process fake_scribbled_exams.pdf"))
    subprocess.check_call(split("plom-scan read -w 4567"))
    subprocess.check_call(split("plom-scan upload -w 4567"))

    time.sleep(0.5)

    print('\n*** Now run "plom-client" ***\n')
    # TODO: output account info directly, perhaps just "user*"?
    print('  (See "serverConfiguration/userListRaw.csv" for acount info)\n')

    print("Starting an endless loop: Ctrl-C to quit demo script")
    # TODO: improve this, catch the ctrl-c and do something
    print("  (you may need to kill the server)")
    while True:
        time.sleep(0.5)


if __name__ == "__main__":
    main()
