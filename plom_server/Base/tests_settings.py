# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.db import IntegrityError
from django.test import TestCase

from .models import SettingsModel


class PapersPrintedSettingTests(TestCase):
    def test_settings_create_rubrics_tristates(self) -> None:
        s = SettingsModel.load()
        s.who_can_create_rubrics = "locked"
        s.save()
        s.who_can_create_rubrics = "permissive"
        s.save()
        s.who_can_create_rubrics = "per-user"
        s.save()

    def test_settings_modify_rubrics_tristates(self) -> None:
        s = SettingsModel.load()
        s.who_can_modify_rubrics = "locked"
        s.save()
        s.who_can_modify_rubrics = "permissive"
        s.save()
        s.who_can_modify_rubrics = "per-user"
        s.save()

    def test_settings_create_rubrics_some_other_state(self) -> None:
        s = SettingsModel.load()
        with self.assertRaises(IntegrityError):
            s.who_can_create_rubrics = None
            s.save()

    def test_settings_modify_rubrics_some_other_state(self) -> None:
        s = SettingsModel.load()
        with self.assertRaises(IntegrityError):
            s.who_can_modify_rubrics = None
            s.save()
