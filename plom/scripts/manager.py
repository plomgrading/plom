#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Stub for a deprecated technique of accessing Plom Manager."""

from warnings import warn

import plom.manager
import plom.manager.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-manager` or `python3 -m plom.manager` directly",
        category=DeprecationWarning,
    )
    plom.manager.__main__.main()
