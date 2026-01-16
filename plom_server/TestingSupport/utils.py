# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald

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

    The papers will be made but this generally doesn't make bundles,
    actual scanned images, etc.
    If you pass `"auto_init_tasks": True` then the tasks will be created,
    but still with no images.

    Args:
        config_input: the configuration is taken from this dict which
            can have various fields.  One important field is
            ``test_spec``, which can be either a string naming a local
            toml file or the path to a toml file, containing a test spec.
            It can also be the string ``"demo"``, which uses a default
            choice.  ``test_sources`` and ``classlist`` behaves similarly.
            Other common fields include ``num_to_produce``, ``qvmap``
            and other things.

    Some lesser-used or perhaps deprecated features:
      * The configuration can also be a single string.  Currently unused
        in practice, but pulls from the `configfiles` directory.
      * I believe this is what the files TestingSupport/config_files/*.toml
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
