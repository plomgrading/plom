# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

from django.test import TestCase

from Base.tests import config_test
from ..services import PQVMappingService


class PQVMappingServiceTests(TestCase):
    @config_test({"test_spec": "config_files/tiny_spec.toml"})
    def test_num_to_produce(self):
        """Test that the created QV Map has the correct number of test-papers."""

        pqvs = PQVMappingService()
        self.assertFalse(pqvs.is_there_a_pqv_map())

        qvmap = pqvs.make_version_map(1)
        self.assertEqual(len(qvmap), 1)
        self.assertEqual(len(qvmap[1]), 2)
