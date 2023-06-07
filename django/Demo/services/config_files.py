# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

import tomlkit


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
            return tomlkit.loads(config_file.read())
