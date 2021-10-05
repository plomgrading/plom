#!/usr/bin/env python3
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020-2021 Andrew Rechnitzer

"""Stub for a deprecated technique of accessing Plom finishing tools."""

import plom.finish
import plom.finish.__main__


if __name__ == "__main__":
    warn(
        "Please use `plom-finish` or `python3 -m plom.finish` directly",
        category=DeprecationWarning,
    )
    plom.finish.__main__.main()
