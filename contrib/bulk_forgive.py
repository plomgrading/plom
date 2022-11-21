#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""Example stand-alone script to communicate with Plom server."""

import os
from pathlib import Path

from plom import __version__
from plom.plom_exceptions import PlomServerNotReady, PlomSeriousException

from plom.create import start_messenger

# from plom.scan import start_messenger


def main():
    print(f"Using Plom {__version__}")

    server = os.environ.get("PLOM_SERVER")
    pwd = os.environ.get("PLOM_MANAGER_PASSWORD")

    msgr = start_messenger(server, pwd)

    # which pages do you want to forgive?  DNM please: very little error checking here
    DNM_pageset = [2, ]

    # largest paper number
    N = 25

    try:
        for papernum in range(1, N + 1):
            for dnm_page in DNM_pageset:
                try:
                    rval = msgr.replaceMissingDNMPage(papernum, dnm_page)
                except PlomSeriousException as e:
                    # TODO: ugh this API has no proper error handling
                    print(f"  Failed papernum {papernum} pg {dnm_page}: maybe b/c no paper or no page: {e}")
                    continue
                # Cleanup, Issue #2141
                print(rval)

    finally:
        msgr.closeUser()
        msgr.stop()


if __name__ == "__main__":
    main()
