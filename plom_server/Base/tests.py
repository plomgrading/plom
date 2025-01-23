# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import pydoc
import re
from functools import wraps
from inspect import getfile
from pathlib import Path

from Demo.services import (
    ConfigFileService,
    ConfigPreparationService,
    ConfigTaskService,
    PlomServerConfig,
)
from django.test import TestCase


class ConfigTestCase(TestCase):
    """Populate the test database with models following a .toml file."""

    # mypy stumbling over Traverseable?  but abc.Traversable added in Python 3.11
    # config_file: str | Path | resources.abc.Traversable | None = None
    config_file: str | Path | None = None

    def setUp(self) -> None:
        if self.config_file is None:
            return

        config = ConfigFileService.read_server_config(self.config_file)
        ConfigPreparationService.create_test_preparation(config)
        ConfigTaskService.init_all_tasks(config)


def config_test(config_input: str | dict | None = None):
    def config_test_decorator(method):
        @wraps(method)
        def wrapper_config_test(self, *args, **kwargs):
            if hasattr(self, "config_file"):
                raise RuntimeError(
                    "Using a class-level config in combination with method-level configs is currently not supported."
                )

            if config_input is None:
                docstring = method.__doc__
                synopsis, config_description = pydoc.splitdoc(docstring)
                config_description = re.split(r"\n\s*", config_description.strip())

                if config_description[0] != "Config:":
                    raise RuntimeError(
                        "Error parsing test method's docstring for server configuration."
                    )

                config_str = "\n".join(config_description[1:])
                parent_dir = Path(getfile(method)).parent
                config = ConfigFileService.read_server_config_from_string(
                    config_str, parent_dir=parent_dir
                )
            elif isinstance(config_input, str):
                config = ConfigFileService.read_server_config(config_input)
            else:
                config_input["parent_dir"] = Path(getfile(method)).parent
                config = PlomServerConfig(**config_input)

            ConfigPreparationService.create_test_preparation(config)
            ConfigTaskService.init_all_tasks(config)
            method(self, *args, **kwargs)

        return wrapper_config_test

    return config_test_decorator
