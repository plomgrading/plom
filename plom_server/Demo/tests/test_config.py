# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from django.test import TestCase

from Demo.services import (
    PlomServerConfig,
    DemoBundleConfig,
    DemoHWBundleConfig,
)


class ServerConfigTests(TestCase):
    """Tests for Demo.ConfigFileService."""

    def test_bad_keys(self):
        """Test the config validation function with unrecognized keys."""
        valid_config = {
            "num_to_produce": 8,
            "test_spec": "demo",
            "parent_dir": ".",
        }
        PlomServerConfig(**valid_config)

        invalid_config = {"n_to_produce": 7, "test_spec": "demo", "parent_dir": "."}

        with self.assertRaises(TypeError):
            # This test is exactly about unexpected args so shutup pylint
            # pylint: disable=unexpected-keyword-arg
            PlomServerConfig(**invalid_config)

    def test_bundle_bad_keys(self):
        """Test the config validation with unrecognized keys in bundles."""
        valid_bundle = {
            "first_paper": 1,
            "last_paper": 1,
        }
        valid_hw_bundle = {
            "paper_number": 1,
            "pages": [[1], [2], [3]],
        }

        DemoBundleConfig(**valid_bundle)
        DemoHWBundleConfig(**valid_hw_bundle)

        invalid_bundle = {
            "frist_paper": 17,  # TODO: intention misspelling? or 17 > 5?
            "last_paper": 5,
        }
        invalid_hw_bundle = {
            "papers": 1,
        }

        with self.assertRaises(TypeError):
            # This test is exactly about unexpected args so shutup pylint
            # pylint: disable=unexpected-keyword-arg
            DemoBundleConfig(**invalid_bundle)

        with self.assertRaises(TypeError):
            # This test is exactly about unexpected args so shutup pylint
            # pylint: disable=unexpected-keyword-arg
            DemoHWBundleConfig(**invalid_hw_bundle)
