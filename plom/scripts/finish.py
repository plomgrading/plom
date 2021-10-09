#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Stub for a deprecated technique of accessing Plom finishing tools."""

from warnings import warn

import plom.finish
import plom.finish.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-finish` or `python3 -m plom.finish` directly",
        category=DeprecationWarning,
    )
    plom.finish.__main__.main()
