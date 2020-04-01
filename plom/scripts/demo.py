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
from textwrap import dedent

from plom import version

def main():
    print("Plom version {}".format(version.__version__))

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

    print('\nNow run "plom-client"')
    # TODO: output account info

    # TODO: keep this running and kill the server on ctrl-C


if __name__ == "__main__":
    main()
