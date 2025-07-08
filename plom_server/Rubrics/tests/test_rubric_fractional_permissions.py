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

    def test_rubrics_create_no_fractions_by_default(self) -> None:
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

    def test_rubrics_create_turn_on_fractions(self) -> None:
        data_quarter = {
            "kind": "relative",
            "value": 1.75,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        data_eighth = {
            "kind": "relative",
            "value": 1.875,
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

    def test_rubrics_modify_turn_on_fractions(self) -> None:
        data_int = {
            "kind": "relative",
            "value": -1,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        r = RubricService._create_rubric(data_int)
        rid = r.rid
        data_eighth = {
            "kind": "relative",
            "value": 1.875,
            "text": "meh",
            "username": "xenia",
            "question_index": 1,
        }
        # OOTB, you cannot modify to fractional
        with self.assertRaises(ValueError):
            RubricService.modify_rubric(rid, data_eighth)

        # enabled 1/4 still gives error
        RubricPermissionsService.change_fractional_settings(
            {"allow-quarter-point-rubrics": "on"}
        )
        with self.assertRaises(ValueError):
            RubricService.modify_rubric(rid, data_eighth)

        # finally enabled 1/8 makes it possible
        RubricPermissionsService.change_fractional_settings(
            {"allow-eighth-point-rubrics": "on"}
        )
        r = RubricService.modify_rubric(rid, data_eighth)

        # if we disable fractions, can still modify it *back* to integer
        RubricPermissionsService.change_fractional_settings(
            {"allow-quarter-point-rubrics": "off", "allow-eighth-point-rubrics": "off"}
        )
        # (as always, need to have the latest revision in our data)
        data_int["revision"] = r["revision"]
        data_int["subrevision"] = r["subrevision"]
        RubricService.modify_rubric(rid, data_int)
