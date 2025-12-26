# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from model_bakery import baker

from ..services import AuthService


class AuthService_user_creation(TestCase):

    def test_create_manager_needs_groups(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-existent Group"):
            AuthService.create_manager_user("manager")

    def test_create_manager(self) -> None:
        # TODO: would a --quiet here give more coverage than using baker?
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        baker.make(Group, name="identifier")
        AuthService.create_manager_user("m")
        user1 = User.objects.get(username="m", groups__name="scanner")
        user2 = User.objects.get(username="m", groups__name="manager")
        self.assertTrue(user1 == user2)

    def test_create_manager_no_password_inactive(self) -> None:
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        baker.make(Group, name="identifier")
        AuthService.create_manager_user("man1")
        user = User.objects.get(username="man1")
        self.assertFalse(user.is_active)
        AuthService.create_manager_user("man2", password="123")
        user = User.objects.get(username="man2")
        self.assertTrue(user.is_active)

    def test_create_manager_via_other_code(self) -> None:
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        baker.make(Group, name="identifier")
        AuthService.create_user_and_add_to_group("m", "manager")
        user1 = User.objects.get(username="m", groups__name="scanner")
        user2 = User.objects.get(username="m", groups__name="manager")
        self.assertTrue(user1 == user2)

    def test_case_insensitive_username_collision(self) -> None:
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        baker.make(Group, name="identifier")
        AuthService.create_user_and_add_to_group("Euler", "manager")
        with self.assertRaises(IntegrityError):
            AuthService.create_user_and_add_to_group("euler", "manager")
        with self.assertRaises(IntegrityError):
            AuthService.create_user_and_add_to_group("euleR", "manager")

    def test_create_admin_fails(self) -> None:
        baker.make(Group, name="admin")
        with self.assertRaisesRegex(ValueError, "Cannot create .*admin"):
            AuthService.create_user_and_add_to_group("Don_Admin", "admin")

    def test_error_to_create_in_non_existing_group(self) -> None:
        baker.make(Group, name="marker")
        with self.assertRaisesRegex(ValueError, "non-existent Group"):
            AuthService.create_user_and_add_to_groups("Marker", ["marker", "foobar"])
        with self.assertRaisesRegex(ValueError, "non-existent Group"):
            AuthService.create_user_and_add_to_groups("Marker", ["foobar"])

    def test_lead_marker_requires_marker(self) -> None:
        baker.make(Group, name="lead_marker")
        baker.make(Group, name="identifier")
        with self.assertRaisesRegex(ValueError, "non-existent Group .*marker"):
            AuthService.create_user_and_add_to_group("Lee_Marker", "lead_marker")

        baker.make(Group, name="marker")
        AuthService.create_user_and_add_to_groups(
            "Lee_Marker2", ["marker", "lead_marker"]
        )

    def test_lead_marker_automatically_implies_marker(self) -> None:
        baker.make(Group, name="marker")
        baker.make(Group, name="identifier")
        baker.make(Group, name="lead_marker")
        AuthService.create_user_and_add_to_group("Lee_Marker", "lead_marker")
