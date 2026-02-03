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
from plom_server.Authentication.services import AuthService
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
        RubricService.modify_rubric(rid, rub, modifying_user=None)

    def test_rubrics_cannot_modify_when_locked(self) -> None:
        yvonne = User.objects.get(username="yvonne")
        xenia = User.objects.get(username="xenia")
        rub = RubricService.create_rubric(_make_ex())
        Settings.set_who_can_modify_rubrics("locked")
        rid = rub["rid"]
        rub.update({"text": "new text"})
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
        xenia = User.objects.get(username="xenia")
        assert r["username"] == xenia.username
        with self.assertRaises(PermissionDenied):
            RubricService.create_rubric(r)
        # we can still make make them using internal mechanisms
        RubricService._create_rubric(r, _bypass_permissions=True)

    def test_rubrics_cannot_create_when_per_user_but_manager_can(self) -> None:
        Settings.set_who_can_create_rubrics("per-user")
        r = _make_ex()
        assert r["username"] == "xenia"
        with self.assertRaisesRegex(PermissionDenied, "xenia.*not allowed"):
            # TODO: capture that xenia is not allowed
            RubricService.create_rubric(r)
        # but another user with enough permissions can override "xenia" (in the rubric data)
        AuthService.create_groups()
        AuthService.create_manager_user("ManaJer")
        manager = User.objects.get(username="ManaJer", groups__name="manager")
        r = RubricService.create_rubric(r, creating_user=manager)
        # the resulting rubric has the creator not xenia
        self.assertNotEqual(r["username"], "xenia")
        self.assertEqual(r["username"], "ManaJer")
