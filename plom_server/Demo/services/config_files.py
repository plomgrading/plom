# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

import tomlkit


class PlomConfigError(Exception):
    """An error for an invalid server config file."""

    pass


class ServerConfigService:
    """Handle building a server database from a config file."""

    def __init__(self):
        self.valid_keys = {
            "test_spec",
            "test_sources",
            "prenaming_enabled",
            "classlist",
            "num_to_produce",
            "bundles",
            "hw_bundles",
        }

        self.valid_bundle_keys = {
            "first_paper",
            "last_paper",
            "extra_page_papers",
            "scrap_page_papers",
            "garbage_page_papers",
            "duplicate_page_papers",
            "wrong_version_papers",
            "duplicate_qr_papers",
            "discard_pages",
        }

        self.valid_hw_bundle_keys = {
            "paper_number",
            "pages",
        }

    def read_server_config(self, path):
        """Create a server config from a TOML file.

        Args:
            path (string or Path-like): location of the config toml file

        Returns:
            dict: a server config.
        """
        with open(path, "r") as config_file:
            try:
                config = tomlkit.loads(config_file.read())
                self.validate_config(config)
                return config
            except tomlkit.exceptions.ParseError as e:
                raise ValueError(e)

    def contains_key(self, config, key):
        """Checks if a top-level key is present in the config.

        Args:
            config (dict): server config.

        Returns:
            bool: true if the key is present, false otherwise
        """
        if key not in self.valid_keys:
            raise ValueError(f"{key} is not a valid key.")
        return key in config.keys()

    def validate_config(self, config):
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
        if not key_set.issubset(self.valid_keys):
            extra_keys = self.valid_keys.difference(key_set)
            raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")

        if "bundles" in config.keys():
            for bundle in config["bundles"]:
                self.validate_bundle(bundle)

        if "hw_bundles" in config.keys():
            for bundle in config["hw_bundles"]:
                self.validate_hw_bundle(bundle)

    def validate_bundle(self, bundle):
        key_set = set(bundle.keys())
        if not key_set.issubset(self.valid_bundle_keys):
            extra_keys = self.valid_bundle_keys.difference(key_set)
            raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")

    def validate_hw_bundle(self, bundle):
        key_set = set(bundle.keys())
        if not key_set.issubset(self.valid_hw_bundle_keys):
            extra_keys = self.valid_hw_bundle_keys.difference(key_set)
            raise PlomConfigError(f"Unrecognized fields in config file: {extra_keys}")
