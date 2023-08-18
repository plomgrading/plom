from django.test import TestCase

from typing import Optional

from Demo.services import ConfigFileService, ConfigPreparationService


class ConfigTestCase(TestCase):
    """Populate the test database with models following a .toml file."""

    config_file: Optional[str] = None

    def setUp(self):
        if self.config_file is None:
            raise RuntimeError("Cannot start a config test case without a toml file.")

        config = ConfigFileService.read_server_config(self.config_file)
        ConfigPreparationService.create_test_preparation(
            config
        )  # TODO: only up to test-papers
