# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.test import TestCase
from django.contrib.auth.models import User, Group
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
        AuthenticationServices().create_user_and_add_to_group("m", "manager")
        user1 = User.objects.get(username="m", groups__name="scanner")
        user2 = User.objects.get(username="m", groups__name="manager")
        self.assertTrue(user1 == user2)
