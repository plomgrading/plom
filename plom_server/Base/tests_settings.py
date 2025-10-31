# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.test import TestCase

from .services import Settings


class TestPapersPrintedSetting(TestCase):
    def test_settings_create_rubrics_tristates(self) -> None:
        Settings.set_who_can_create_rubrics("locked")
        Settings.set_who_can_create_rubrics("permissive")
        Settings.set_who_can_create_rubrics("per-user")

    def test_settings_modify_rubrics_tristates(self) -> None:
        Settings.set_who_can_modify_rubrics("locked")
        Settings.set_who_can_modify_rubrics("permissive")
        Settings.set_who_can_modify_rubrics("per-user")

    def test_settings_create_rubrics_some_other_state(self) -> None:
        with self.assertRaises(ValueError):
            Settings.set_who_can_create_rubrics("meh")

    def test_settings_modify_rubrics_some_other_state(self) -> None:
        with self.assertRaises(ValueError):
            Settings.set_who_can_modify_rubrics("foobar")
