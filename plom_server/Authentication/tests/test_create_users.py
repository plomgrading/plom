# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from model_bakery import baker

from ..services import AuthenticationServices


class AuthenticationServices_user_creation(TestCase):

    def test_create_manager_needs_groups(self) -> None:
        with self.assertRaisesRegex(ValueError, "group .* not .* created"):
            AuthenticationServices.create_manager_user("manager")

    def test_create_manager(self) -> None:
        # TODO: would a --quiet here give more coverage than using baker?
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        AuthenticationServices.create_manager_user("m")
        user1 = User.objects.get(username="m", groups__name="scanner")
        user2 = User.objects.get(username="m", groups__name="manager")
        self.assertTrue(user1 == user2)

    def test_create_manager_no_password_inactive(self) -> None:
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        AuthenticationServices.create_manager_user("man1")
        user = User.objects.get(username="man1")
        self.assertFalse(user.is_active)
        AuthenticationServices.create_manager_user("man2", password="123")
        user = User.objects.get(username="man2")
        self.assertTrue(user.is_active)

    def test_create_manager_via_other_code(self) -> None:
        # call_command("plom_create_groups")
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        AuthenticationServices.create_user_and_add_to_group("m", "manager")
        user1 = User.objects.get(username="m", groups__name="scanner")
        user2 = User.objects.get(username="m", groups__name="manager")
        self.assertTrue(user1 == user2)

    def test_case_insensitive_username_collision(self) -> None:
        baker.make(Group, name="manager")
        baker.make(Group, name="scanner")
        AuthenticationServices.create_user_and_add_to_group("Euler", "manager")
        with self.assertRaises(IntegrityError):
            AuthenticationServices.create_user_and_add_to_group("euler", "manager")
        with self.assertRaises(IntegrityError):
            AuthenticationServices.create_user_and_add_to_group("euleR", "manager")

    def test_create_admin_fails(self) -> None:
        baker.make(Group, name="admin")
        with self.assertRaises(ValueError):
            AuthenticationServices.create_user_and_add_to_group("Don_Admin", "admin")

    def test_lead_marker_requires_marker(self) -> None:
        baker.make(Group, name="lead_marker")
        with self.assertRaises(ObjectDoesNotExist):
            AuthenticationServices.create_user_and_add_to_group(
                "Lee_Marker", "lead_marker"
            )

        baker.make(Group, name="marker")
        AuthenticationServices.create_user_and_add_to_group("Lee_Marker", "lead_marker")
