# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.test import TestCase

from typing import Optional, Callable
from functools import wraps
from pathlib import Path
import pydoc
import re
from inspect import getfile

from Demo.services import ConfigFileService, ConfigPreparationService


class ConfigTestCase(TestCase):
    """Populate the test database with models following a .toml file."""

    config_file: Optional[str] = None

    def setUp(self):
        if self.config_file is None:
            return

        config = ConfigFileService.read_server_config(self.config_file)
        ConfigPreparationService.create_test_preparation(
            config
        )  # TODO: only up to test-papers


def config_test(config_path=None):
    def config_test_decorator(method):
        @wraps(method)
        def wrapper_config_test(self, *args, **kwargs):
            if hasattr(self, "config_file"):
                raise RuntimeError(
                    "Using a class-level config in combination with method-level configs is currently not supported."
                )

            if config_path is None:
                docstring = method.__doc__
                synopsis, config_description = pydoc.splitdoc(docstring)
                config_description = re.split("\n\s*", config_description.strip())

                if config_description[0] != "Config:":
                    raise RuntimeError(
                        "Error parsing test method's docstring for server configuration."
                    )

                config_str = "\n".join(config_description[1:])
                parent_dir = Path(getfile(method)).parent
                config = ConfigFileService.read_server_config_from_string(
                    config_str, parent_dir=parent_dir
                )
            else:
                config = ConfigFileService.read_server_config(config_path)

            ConfigPreparationService.create_test_preparation(config)
            method(self, *args, **kwargs)

        return wrapper_config_test

    return config_test_decorator
