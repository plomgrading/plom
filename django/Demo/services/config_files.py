# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

import tomlkit


class PlomConfigError(Exception):
    """An error for an invalid server config file."""

    pass


class ServerConfigService:
    """Handle building a server database from a config file."""

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
