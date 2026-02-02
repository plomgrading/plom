# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2025 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from model_bakery import baker

from plom_server.Base.services import Settings
from plom_server.TestingSupport.utils import config_test
from ..services import RubricService


def _make_ex():
    """Simulate input e.g., from client."""
    return {
        "username": "xenia",
        "kind": "neutral",
        "display_delta": ".",
        "text": "ABC",
        "question_index": 1,
    }


class RubricServiceTests_permissions(TestCase):
    """Tests related to rubric permissions."""

    @config_test({"test_spec": "demo"})
    def setUp(self) -> None:
        baker.make(User, username="xenia")
        baker.make(User, username="yvonne")

    def test_rubrics_None_user_can_modify_when_locked(self) -> None:
        Settings.set_who_can_modify_rubrics("locked")
        rub = RubricService.create_rubric(_make_ex())
        rid = rub["rid"]
        rub.update({"text": "new text"})
        # succeeded b/c user is None
        RubricService.modify_rubric(rid, rub, modifying_user=None)

    def test_rubrics_cannot_modify_when_locked(self) -> None:
        Settings.set_who_can_modify_rubrics("locked")
        rub = RubricService.create_rubric(_make_ex())
        rid = rub["rid"]
        rub.update({"text": "new text"})
        yvonne = User.objects.get(username="yvonne")
        xenia = User.objects.get(username="xenia")
        with self.assertRaises(PermissionDenied):
            RubricService.modify_rubric(rid, rub, modifying_user=yvonne)
        # even creator cannot modify
        with self.assertRaises(PermissionDenied):
            RubricService.modify_rubric(rid, rub, modifying_user=xenia)

    def test_rubrics_permissive_cannot_modify_system_rubrics(self) -> None:
        Settings.set_who_can_modify_rubrics("permissive")
        rub = _make_ex()
        rub.update({"system_rubric": True})
        rub = RubricService.create_rubric(rub)
        rid = rub["rid"]
        rub.update({"text": "trying to change a system rubric"})
        xenia = User.objects.get(username="xenia")
        with self.assertRaises(PermissionDenied):
            RubricService.modify_rubric(rid, rub, modifying_user=xenia)

    def test_rubrics_cannot_create_when_locked(self) -> None:
        Settings.set_who_can_create_rubrics("locked")
        r = _make_ex()
        with self.assertRaises(PermissionDenied):
            RubricService.create_rubric(r, creating_user=r["username"])
        # we can still make make them with None for internal use
        RubricService.create_rubric(r, creating_user=None)
