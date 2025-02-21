# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.test import TestCase

from ..services import (
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

    def test_bundle_ok_keys(self):
        valid_bundle = {
            "first_paper": 1,
            "last_paper": 1,
        }
        DemoBundleConfig(**valid_bundle)
        valid_hw_bundle = {
            "paper_number": 1,
            "pages": [[1], [2], [3]],
        }
        DemoHWBundleConfig(**valid_hw_bundle)

    def test_bundle_bad_keys(self):
        """Test the config validation with unrecognized keys in bundles."""
        invalid_bundle = {
            "frist_paper": 2,  # intention misspelling
            "last_paper": 5,
        }
        with self.assertRaises(TypeError):
            # This test is exactly about unexpected args so shutup pylint
            # pylint: disable=unexpected-keyword-arg
            DemoBundleConfig(**invalid_bundle)

        invalid_hw_bundle = {
            "ony_one_wrong_key": 1,
        }
        with self.assertRaises(TypeError):
            # This test is exactly about unexpected args so shutup pylint
            # pylint: disable=unexpected-keyword-arg
            DemoHWBundleConfig(**invalid_hw_bundle)
