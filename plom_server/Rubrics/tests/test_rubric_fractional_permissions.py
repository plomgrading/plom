# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.contrib.auth.models import User
from django.test import TestCase

from model_bakery import baker

from plom_server.Base.tests import config_test
from ..services import RubricService, RubricPermissionsService


def _make_ex():
    """Simulate input e.g., from client."""
    return {
        "username": "xenia",
        "kind": "neutral",
        "display_delta": ".",
        "text": "ABC",
        "question_index": 1,
    }


class RubricServiceTests_fractional_permissions(TestCase):
    """Tests related to rubric permissions."""

    @config_test({"test_spec": "demo"})
    def setUp(self) -> None:
        baker.make(User, username="xenia")

    def test_rubrics_no_fractions_by_default(self) -> None:
        data_half = {
            "kind": "relative",
            "value": 1.5,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        # TODO: do we really want ValueError?
        with self.assertRaises(ValueError):
            RubricService._create_rubric(data_half)

    def test_rubrics_turn_on_fractions(self) -> None:
        data_quarter = {
            "kind": "relative",
            "value": 1.75,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        data_eighth = {
            "kind": "relative",
            "value": 1.825,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        with self.assertRaises(ValueError):
            RubricService._create_rubric(data_quarter)
        RubricPermissionsService.change_fractional_settings(
            {"allow-quarter-point-rubrics": "on"}
        )
        RubricService._create_rubric(data_quarter)
        with self.assertRaises(ValueError):
            RubricService._create_rubric(data_eighth)
