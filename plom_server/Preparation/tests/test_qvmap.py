# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.test import TestCase
from django.conf import settings

from Papers.services import SpecificationService
from ..services import PQVMappingService


class PQVMappingServiceTests(TestCase):
    def setUp(self):
        toml_path = (
            settings.BASE_DIR
            / "Preparation"
            / "useful_files_for_testing"
            / "testing_test_spec.toml"
        )
        SpecificationService.load_spec_from_toml(toml_path)

    def test_num_to_produce(self):
        """Test that the created QV Map has the correct number of test-papers."""

        pqvs = PQVMappingService()
        self.assertFalse(pqvs.is_there_a_pqv_map())

        qvmap = pqvs.make_version_map(1)
        self.assertEqual(len(qvmap), 1)
        self.assertEqual(len(qvmap[1]), 3)
