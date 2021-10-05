#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Stub for a deprecated technique of accessing scanning tools."""

from warnings import warn

import plom.scan
import plom.scan.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-scan` or `python3 -m plom.scan` directly",
        category=DeprecationWarning,
    )
    plom.scan.__main__.main()
