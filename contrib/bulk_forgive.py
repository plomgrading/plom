#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""Stand-alone script to give all non-scanned do-not-mark papers.

Use at your own risk.
"""

import os
from pathlib import Path

from plom import __version__
from plom.plom_exceptions import PlomServerNotReady, PlomSeriousException

from plom.create import start_messenger


def main():
    print(f"Using Plom {__version__}")

    server = os.environ.get("PLOM_SERVER")
    pwd = os.environ.get("PLOM_MANAGER_PASSWORD")

    msgr = start_messenger(server, pwd)

    # which pages do you want to forgive?  DNM please: very little error checking here
    DNM_pageset = (2,)

    try:
        incomplete = msgr.getIncompleteTests()  # triples [p,v,true/false]
        for papernum, X in incomplete.items():
            papernum = int(papernum)
            # [['t.1', 1, True], ['t.2', 1, False], ['t.3', 1, True], ...]
            for pagestr, version, scanned in X:
                if not scanned:
                    # TODO now we should official check if that is a DNM page but instead
                    # I will blindly trust the DNM_pageset
                    for p in DNM_pageset:
                        if f"t.{p}" == pagestr:
                            print(
                                f"{papernum:04} pg {pagestr} missing and is a DNM page: replacing..."
                            )
                            rval = msgr.replaceMissingDNMPage(papernum, p)
                            # Cleanup, Issue #2141
                            print(rval)
                    else:
                        print(
                            f"{papernum:04} pg {pagestr} missing: but its not a DNM page: no-op"
                        )

    finally:
        msgr.closeUser()
        msgr.stop()


if __name__ == "__main__":
    main()
