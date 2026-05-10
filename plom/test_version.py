# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023-2026 Colin B. Macdonald

from packaging.version import Version

from plom.misc_version import __version__


def test_valid_version() -> None:
    Version(__version__)
