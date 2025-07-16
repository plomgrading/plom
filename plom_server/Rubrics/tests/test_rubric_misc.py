# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.test import TestCase

from ..services.utils import fractional_part_is_nth, pin_to_fractional_nth


class RubricServiceTests_misc(TestCase):
    """Tests related to misc or utilities of rubrics."""

    def test_fractional_part(self) -> None:
        self.assertTrue(fractional_part_is_nth(1.3333333333333, 3))
        self.assertTrue(fractional_part_is_nth(1.6666666666667, 3))
        self.assertTrue(fractional_part_is_nth(1.25, 4))
        self.assertTrue(fractional_part_is_nth(1.25, 8))
        self.assertTrue(fractional_part_is_nth(1.125, 8))
        self.assertTrue(fractional_part_is_nth(1.2, 5))
        self.assertTrue(fractional_part_is_nth(1.2, 10))
        self.assertTrue(fractional_part_is_nth(1.1, 10))
        self.assertFalse(fractional_part_is_nth(1.1, 5))

    def test_fractional_part_negative(self) -> None:
        self.assertTrue(fractional_part_is_nth(-1.3333333333333, 3))
        self.assertTrue(fractional_part_is_nth(-1.6666666666667, 3))
        self.assertTrue(fractional_part_is_nth(-1.25, 4))

    def test_fractional_part_tolerance_not_too_loose(self) -> None:
        self.assertFalse(fractional_part_is_nth(1.33, 3))
        self.assertFalse(fractional_part_is_nth(1.333, 3))
        self.assertTrue(fractional_part_is_nth(1.333333333333, 3))

    def test_fractional_part_accurate_value(self) -> None:
        pin = pin_to_fractional_nth
        self.assertAlmostEqual(pin(1.1, 10), 11.0 / 10)
        self.assertTrue(abs(pin(1.1, 10) - 11.0 / 10) <= 1e-15)

        self.assertAlmostEqual(pin(-1.666666667, 3), -5.0 / 3)
        self.assertTrue(abs(pin(1.1, 10) - 11.0 / 10) <= 1e-15)
