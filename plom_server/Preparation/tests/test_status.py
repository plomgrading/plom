# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.test import TestCase

from ..services import TestPreparedSetting
from ..models import TestPreparedSettingModel


class PreparedSettingTests(TestCase):
    def test_is_prepared(self):
        """Test the is_prepared getter function."""
        self.assertFalse(TestPreparedSetting.is_test_prepared())

        setting_obj = TestPreparedSettingModel.load()
        setting_obj.finished = True
        setting_obj.save()

        self.assertTrue(TestPreparedSetting.is_test_prepared())

    def test_set_prepared(self):
        """Test the prepared setter function.

        TODO: Should the setter function check the state of the Papers table first? Or should we assume parent functions + the UI will take care of that?
        """
        setting_obj = TestPreparedSettingModel.load()
        self.assertFalse(setting_obj.finished)

        TestPreparedSetting.set_test_prepared(True)

        setting_obj.refresh_from_db()
        self.assertTrue(setting_obj.finished)

        TestPreparedSetting.set_test_prepared(False)

        setting_obj.refresh_from_db()
        self.assertFalse(setting_obj.finished)
