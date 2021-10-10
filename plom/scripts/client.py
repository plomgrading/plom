#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

"""Stub for a deprecated technique of accessing Plom Client."""

from warnings import warn

import plom.client
import plom.client.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-client` or `python3 -m plom.client` directly",
        category=DeprecationWarning,
    )
    plom.client.__main__.main()
