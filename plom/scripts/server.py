#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Stub for a deprecated technique of accessing Plom servers."""

from warnings import warn

import plom.server
import plom.server.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-server` or `python3 -m plom.server` directly",
        category=DeprecationWarning,
    )
    plom.server.__main__.main()
