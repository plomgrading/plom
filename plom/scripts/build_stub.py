#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

"""Stub for a deprecated technique of accessing building tools."""

from warnings import warn

import plom.create
import plom.create.__main__


def main():
    warn(
        "Please use `plom-create` or `python3 -m plom.create` directly",
        category=DeprecationWarning,
    )
    # not sure why this warn doesn't show up, so print instead:
    print(
        'Warning: "plom-build" is deprecated: use `plom-create` or `python3 -m plom.create`'
    )
    plom.create.__main__.main()


if __name__ == "__main__":
    warn(
        "Please use `plom-create` or `python3 -m plom.create` directly",
        category=DeprecationWarning,
    )
    plom.create.__main__.main()
