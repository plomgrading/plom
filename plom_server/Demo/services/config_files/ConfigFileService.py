# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

"""Handle building a server database from a config file."""

from typing import Union
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from . import PlomConfigError


valid_keys = {
    "test_spec",
    "test_sources",
    "prenaming_enabled",
    "classlist",
    "num_to_produce",
    "bundles",
    "hw_bundles",
}


valid_bundle_keys = {
    "first_paper",
    "last_paper",
    "extra_page_papers",
    "garbage_page_papers",
    "duplicate_page_papers",
    "wrong_version_papers",
    "duplicate_qr_papers",
    "discard_pages",
}


valid_hw_bundle_keys = {
    "paper_number",
    "pages",
}


def read_server_config(path: Union[str, Path]) -> dict:
    """Create a server config from a TOML file.

    Args:
        path (string or Path-like): location of the config toml file

    Returns:
        dict: a server config.
    """
    with open(path, "rb") as config_file:
        try:
            config = tomllib.load(config_file)
            validate_config(config)
            return config
        except tomllib.TOMLDecodeError as e:
            raise ValueError(e)


def contains_key(config: dict, key: str) -> bool:
    """Checks if a top-level key is present in the config.

    Args:
        config (dict): server config.
        key (str): the key to query

    Returns:
        bool: true if the key is present, false otherwise
    """
    if key not in valid_keys:
        raise ValueError(f"{key} is not a valid key.")
    return key in config.keys()


def validate_config(config: dict) -> None:
    """Validate a server config file."""
    if "test_spec" not in config.keys():
        raise PlomConfigError(
            "A test specification is required in order to build a server."
        )

    if "bundles" in config.keys() or "hw_bundles" in config.keys():
        if "test_sources" not in config.keys():
            raise PlomConfigError(
                "Bundles are specified but the config lacks a test_sources field."
            )
        if "num_to_produce" not in config.keys():
            raise PlomConfigError(
                "Bundles are specified but the config lacks a num_to_produce field."
            )

    key_set = set(config.keys())
    if not key_set.issubset(valid_keys):
        extra_keys = valid_keys.difference(key_set)
        raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")

    if "bundles" in config.keys():
        for bundle in config["bundles"]:
            validate_bundle(bundle)

    if "hw_bundles" in config.keys():
        for bundle in config["hw_bundles"]:
            validate_hw_bundle(bundle)


def validate_bundle(bundle: dict) -> None:
    key_set = set(bundle.keys())
    if not key_set.issubset(valid_bundle_keys):
        extra_keys = valid_bundle_keys.difference(key_set)
        raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")


def validate_hw_bundle(bundle: dict) -> None:
    key_set = set(bundle.keys())
    if not key_set.issubset(valid_hw_bundle_keys):
        extra_keys = valid_hw_bundle_keys.difference(key_set)
        raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")
