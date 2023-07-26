# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.test import TestCase
from model_bakery import baker

from ..services import StagingStudentService, PrenameSettingService
from ..models import StagingStudent


class StagingStudentsTests(TestCase):
    def test_get_minimum_number_to_produce(self):
        """Test StagingStudentService.get_minimum_number_to_produce()."""
        sstu = StagingStudentService()
        min_to_produce = sstu.get_minimum_number_to_produce()
        self.assertEqual(min_to_produce, 20)

        baker.make(StagingStudent, paper_number=25, _quantity=10)

        min_to_produce = sstu.get_minimum_number_to_produce()
        self.assertEqual(min_to_produce, 30)

        pre = PrenameSettingService()
        pre.set_prenaming_setting(True)

        min_to_produce = sstu.get_minimum_number_to_produce()
        self.assertEqual(min_to_produce, 35)
