# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from functools import wraps
from inspect import getfile
from pathlib import Path

from .services import (
    ConfigFileService,
    ConfigPreparationService,
    ConfigTaskService,
    PlomServerConfig,
)


def config_test(config_input: str | dict | None = None):
    """This decorator loads a configuration from dictionary for testing.

    You can apply it to individual methods or to the `setUp()` method of
    your Test class.

    Args:
        config_input: the configuration is taken from this dict which
            can have various fields which are presumably documented
            somewhere...

    Some lesser-used or perhaps deprecated features:
      * The configuration can also be a single string.  TODO: Unused?
      * I believe this is what the files TestingSupport/config_files/*.tom;
        are supposed to be for.  But nothing is using them right now...?
    """

    def config_test_decorator(method):
        @wraps(method)
        def wrapper_config_test(self, *args, **kwargs):
            if config_input is None:
                raise RuntimeError("No default config is currently defined")
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
