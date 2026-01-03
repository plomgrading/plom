# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald

from django.test import TestCase
from model_bakery import baker

from ..services import StagingStudentService
from ..models import StagingStudent


class StagingStudentsTests(TestCase):
    def test_get_minimum_number_to_produce(self) -> None:
        """Test StagingStudentService.get_minimum_number_to_produce()."""
        sstu = StagingStudentService()
        min_to_produce = sstu.get_minimum_number_to_produce()
        self.assertEqual(min_to_produce, 20)

        baker.make(StagingStudent, paper_number=25, _quantity=10)

        min_to_produce = sstu.get_minimum_number_to_produce()
        self.assertEqual(min_to_produce, 35)

    def test__minimum_number_to_produce_typing(self) -> None:
        """Test type handling of _minimum_number_to_produce()."""
        # arg 1: num_students, arg 2: highest prenamed paper
        calc_minimum = StagingStudentService._minimum_number_to_produce

        # check that None doesn't throw errors
        calc_minimum(-20, None)
        calc_minimum(-20, None)

        # check that return type is int
        assert isinstance(calc_minimum(10, 5), int)
        assert isinstance(calc_minimum(250, 5), int)
        assert isinstance(calc_minimum(10, 25), int)

    def test__minimum_number_to_produce_logic(self) -> None:
        """Test internal logic of _minimum_number_to_produce()."""
        # arg 1: num_students, arg 2: highest prenamed paper
        calc_minimum = StagingStudentService._minimum_number_to_produce

        # for small sittings, minimum should be 20 extra
        self.assertEqual(calc_minimum(0), 20)
        self.assertEqual(calc_minimum(199), 219)

        # for large sittings, minimum 10% extra (rounded up)
        self.assertEqual(calc_minimum(201), 222)

        # with prenaming, prior rules or highest prenamed paper + 10
        # for small sittings
        self.assertEqual(calc_minimum(0, 5), 20)
        self.assertEqual(calc_minimum(0, 15), 25)
        self.assertEqual(calc_minimum(199, 5), 219)
        self.assertEqual(calc_minimum(199, 215), 225)

        # for large sittings
        self.assertEqual(calc_minimum(201, 5), 222)  # rounding up
        self.assertEqual(calc_minimum(201, 219), 229)

    def test_valid_paper_number_sentinels(self) -> None:
        n = 10000000
        for p in (None, -1, "", "-1"):
            n += 1
            sid = str(n)
            StagingStudentService._add_student(sid, "mdme X", paper_number=p)

    def test_valid_paper_number_integers_in_strings(self) -> None:
        n = 10000000
        n += 1
        StagingStudentService._add_student(str(n), "X", paper_number=17)
        n += 1
        StagingStudentService._add_student(str(n), "X", paper_number="17")
        n += 1
        with self.assertRaises(ValueError):
            StagingStudentService._add_student(str(n), "X", paper_number="MCML")
