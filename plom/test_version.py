# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023-2024 Colin B. Macdonald

from packaging.version import Version
from plom import __version__


def test_valid_version() -> None:
    Version(__version__)
