#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""Stub for a deprecated technique of accessing demo."""

from warnings import warn

import plom.demo
import plom.demo.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-demo` or `python3 -m plom.demo` directly",
        category=DeprecationWarning,
    )
    plom.demo.__main__.main()
