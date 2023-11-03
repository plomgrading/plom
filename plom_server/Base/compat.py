# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

"""A module for backwards compatibility support.

See https://github.com/encode/django-rest-framework/blob/master/rest_framework/compat.py
for a similar module in Django REST Framework.
"""

from pathlib import Path
from typing import Union, Any, Dict
import sys


class TOMLDecodeError(Exception):
    """A library-independent TOML decoding exception."""

    pass


def load_toml_from_path(path: Union[str, Path]) -> Dict[str, Any]:
    """Get a dictionary by reading a TOML file from disk."""
    if sys.version_info < (3, 11):
        import tomli as tomllib
    else:
        import tomllib

    try:
        with open(path, "rb") as toml_file:
            return tomllib.load(toml_file)
    except tomllib.TOMLDecodeError as e:
        raise TOMLDecodeError(e)


def load_toml_from_string(toml_string: str) -> Dict[str, Any]:
    """Get a dictionary by reading a TOML string directly."""
    if sys.version_info < (3, 11):
        import tomli as tomllib
    else:
        import tomllib

    try:
        return tomllib.loads(toml_string)
    except tomllib.TOMLDecodeError as e:
        raise TOMLDecodeError(e)
