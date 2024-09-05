# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.test import TestCase
from model_bakery import baker

from ..services import StagingStudentService, PrenameSettingService
from ..models import StagingStudent


class StagingStudentsTests(TestCase):
    def test_get_minimum_number_to_produce(self) -> None:
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

    def test_valid_paper_number_sentinels(self) -> None:
        n = 10000000
        for p in (None, -1, "", "-1"):
            n += 1
            sid = str(n)
            StagingStudentService()._add_student(sid, "mdme X", paper_number=p)

    def test_valid_paper_number_integers_in_strings(self) -> None:
        n = 10000000
        n += 1
        StagingStudentService()._add_student(str(n), "X", paper_number=17)
        n += 1
        StagingStudentService()._add_student(str(n), "X", paper_number="17")
        n += 1
        with self.assertRaises(ValueError):
            StagingStudentService()._add_student(str(n), "X", paper_number="MCML")
