# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import unicodedata
from fractions import Fraction

from django.test import TestCase

from ..services.rubric_service import _fraction_table
from ..services.rubric_service import _generate_display_delta as gen_display


class RubricServiceTests_display_delta(TestCase):

    def test_table_correctness(self) -> None:
        # avoid typos in the fraction table by computing values
        for frac, s in _fraction_table:
            assert isinstance(frac, float)
            assert isinstance(s, str)
            if len(s) == 1:
                value: float | Fraction = unicodedata.numeric(s)
                continue
            try:
                value = Fraction(s)
            except ValueError:
                # split on \N{Fraction Slash}, construct fraction
                def c2n(d: str) -> int:
                    return round(unicodedata.numeric(d))

                num, den = s.split("\N{FRACTION SLASH}")
                numint = sum([c2n(d) * 10**i for i, d in enumerate(num[::-1])])
                denint = sum([c2n(d) * 10**i for i, d in enumerate(den[::-1])])
                value = Fraction(numint, denint)
            self.assertAlmostEqual(value, frac)

    def test_generate_display_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid kind"):
            gen_display(0, "some_invalid_kind")
        with self.assertRaises(ValueError):
            gen_display(0, "absolute")

    def test_generate_display_neutal(self) -> None:
        self.assertEqual(gen_display(1, "neutral"), ".")

    def test_generate_display_relative(self) -> None:
        self.assertEqual(gen_display(1, "relative"), "+1")
        self.assertEqual(gen_display(-2, "relative"), "-2")
        self.assertEqual(gen_display(-0.25, "relative"), "-¼")
        self.assertEqual(gen_display(0.75, "relative"), "+¾")

    def test_generate_display_relative_decimals(self) -> None:
        self.assertEqual(gen_display(-2.0, "relative"), "-2")
        self.assertEqual(gen_display(-2.35, "relative"), "-2.35")
        self.assertEqual(gen_display(2.0, "relative"), "+2")
        self.assertEqual(gen_display(2.35, "relative"), "+2.35")

    def test_generate_display_absolute(self) -> None:
        self.assertEqual(gen_display(1, "absolute", 2), "1 of 2")
        self.assertEqual(gen_display(0.5, "absolute", 2), "½ of 2")
        self.assertEqual(gen_display(1.3, "absolute", 2), "1.3 of 2")
        self.assertEqual(gen_display(1.3, "absolute", 2.0), "1.3 of 2")

    def test_generate_display_mixed_fractions(self) -> None:
        self.assertIn(gen_display(1.5, "absolute", 2), ("1.5 of 2", "1½ of 2"))

    def test_generate_display_fractional_out_of(self) -> None:
        self.assertEqual(gen_display(0, "absolute", 0.5), "0 of ½")
        self.assertEqual(gen_display(0.25, "absolute", 0.5), "¼ of ½")

    def test_generate_display_fraction_tolerance(self) -> None:
        self.assertEqual(gen_display(2 / 3, "relative"), "+⅔")
        self.assertEqual(gen_display(0.666666666667, "relative"), "+⅔")
        self.assertEqual(gen_display(0.66666667, "relative"), "+⅔")
        self.assertEqual(gen_display(0.333333333333, "relative"), "+⅓")
        self.assertEqual(gen_display(0.33333333, "relative"), "+⅓")
        self.assertEqual(gen_display(0.667, "relative"), "+0.667")
        self.assertEqual(gen_display(0.333, "relative"), "+0.333")
