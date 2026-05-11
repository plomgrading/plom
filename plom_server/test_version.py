# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023-2026 Colin B. Macdonald

from packaging.version import Version

from plom_server import __version__
from plom.misc_version import __version__ as another_version


def test_valid_version() -> None:
    Version(__version__)


def test_version_two_copes_match() -> None:
    assert Version(__version__) == Version(another_version)
