# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer

from django.test import TestCase
from model_bakery import baker

from Papers.models import Paper, Bundle

from ..services import PapersPrinted
from ..models import PapersPrintedSettingModel


class PapersPrintedSettingTests(TestCase):
    def test_can_be_set_as_printed(self):
        """Test can_status_be_set_true.

        Should return false if the Paper table is empty.
        """
        self.assertFalse(PapersPrinted.can_status_be_set_true())

        baker.make(Paper)

        self.assertTrue(PapersPrinted.can_status_be_set_true())

    def test_can_be_set_false(self):
        """Test can_status_be_set_false.

        Should return false if the Bundle table isn't empty.
        """
        self.assertTrue(PapersPrinted.can_status_be_set_false())

        baker.make(Bundle)

        self.assertFalse(PapersPrinted.can_status_be_set_false())

    def test_is_prepared(self):
        """Test the is_prepared getter function."""
        self.assertFalse(PapersPrinted.have_papers_been_printed())

        setting_obj = PapersPrintedSettingModel.load()
        setting_obj.finished = True
        setting_obj.save()

        self.assertTrue(PapersPrinted.have_papers_been_printed())

    def test_set_prepared(self):
        """Test the prepared setter function."""
        baker.make(Paper)

        setting_obj = PapersPrintedSettingModel.load()
        self.assertFalse(setting_obj.finished)

        PapersPrinted.set_test_prepared(True)

        setting_obj.refresh_from_db()
        self.assertTrue(setting_obj.finished)

        PapersPrinted.set_test_prepared(False)

        setting_obj.refresh_from_db()
        self.assertFalse(setting_obj.finished)

    def test_setting_raises_papers(self):
        """Make sure the setting raises an error on being set true while the papers database is empty."""
        with self.assertRaises(RuntimeError):
            PapersPrinted.set_test_prepared(True)

        baker.make(Paper)
        PapersPrinted.set_test_prepared(True)

    def test_setting_raises_bundles(self):
        """Make sure the setting raises an error on being set false while bundles are in the database."""
        baker.make(Paper)
        PapersPrinted.set_test_prepared(True)

        bundle = baker.make(Bundle)
        with self.assertRaises(RuntimeError):
            PapersPrinted.set_test_prepared(False)

        bundle.delete()
        PapersPrinted.set_test_prepared(False)
