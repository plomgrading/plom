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

from plom import version


def main():
    print("Plom version {}".format(version.__version__))

    # TODO: MAYBE DISABLE THIS SCARY STUFF?
    # TODO: user runs in new empty dir or get's all pieces...
    # TODO: or better yet, check that these subdirs DNE
    for f in (
        "specAndDatabase/plom.db",
        "specAndDatabase/classlist.csv",
        "serverConfiguration/userListRaw.csv",
        "serverConfiguration/userList.json",
        "archivedPDFs/fake_scribbled_exams.pdf",
    ):
        print("Erasing {}".format(f))
        try:
            os.remove(f)
        except OSError:
            pass

    subprocess.check_call(split("plom-build new --demo"))
    subprocess.check_call(split("plom-build make"))
    subprocess.check_call(split("plom-build class --demo"))
    subprocess.check_call(split("plom-fake-scribbles"))
    subprocess.check_call(split("plom-server init"))
    subprocess.check_call(split("plom-server users --demo"))

    # TODO: have to put this in the background before we can upload
    subprocess.Popen(split("plom-server launch"))
    subprocess.check_call(split("plom-scan process fake_scribbled_exams.pdf"))
    subprocess.check_call(split("plom-scan read -w 4567"))
    subprocess.check_call(split("plom-scan upload -w 4567"))

    print('\n*** Now run "plom-client" ***\n')
    # TODO: output account info

    print("Starting an endless loop: Ctrl-C to quit demo script")
    # TODO: keep this running and kill the server on ctrl-C
    while True:
        time.sleep(0.5)


if __name__ == "__main__":
    main()
