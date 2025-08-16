# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.test import TestCase
from model_bakery import baker

from plom_server.Base.services import Settings
from plom_server.Papers.models import Paper, Bundle

from ..services import PapersPrinted

from unittest import skip


# TODO - all of these test need rewriting for the newer
# method of dependency checking
@skip("These tests need rewriting after the updates for dependency checking.")
class PapersPrintedSettingTests(TestCase):
    # Commenting these out until they get rewritten
    # for the new dependency checking method

    # def test_can_be_set_as_printed(self) -> None:
    #     """Test can_status_be_set_true.
    #
    #     Should return false if the Paper table is empty.
    #     """
    #     self.assertFalse(PapersPrinted.can_status_be_set_true())
    #
    #     baker.make(Paper)
    #
    #     self.assertTrue(PapersPrinted.can_status_be_set_true())
    #
    # def test_can_be_set_false(self) -> None:
    #     """Test can_status_be_set_false.
    #
    #     Should return false if the Bundle table isn't empty.
    #     """
    #     self.assertTrue(PapersPrinted.can_status_be_set_false())
    #
    #     baker.make(Bundle)
    #
    #     self.assertFalse(PapersPrinted.can_status_be_set_false())

    def test_papers_printed(self) -> None:
        """Test the papers_printed setter function."""
        baker.make(Paper)

        r = Settings.key_value_store_get("papers_have_been_printed")
        self.assertFalse(r)

        PapersPrinted.set_papers_printed(True)

        r = Settings.key_value_store_get("papers_have_been_printed")
        self.assertTrue(r)

        PapersPrinted.set_papers_printed(False)

        r = Settings.key_value_store_get("papers_have_been_printed")
        self.assertFalse(r)

    def test_setting_raises_papers(self) -> None:
        """Make sure the setting raises an error on being set true while the papers database is empty."""
        with self.assertRaises(RuntimeError):
            PapersPrinted.set_papers_printed(True)

        baker.make(Paper)
        PapersPrinted.set_papers_printed(True)

    def test_setting_raises_bundles(self) -> None:
        """Make sure the setting raises an error on being set false while bundles are in the database."""
        baker.make(Paper)
        PapersPrinted.set_papers_printed(True)

        bundle = baker.make(Bundle)
        with self.assertRaises(RuntimeError):
            PapersPrinted.set_papers_printed(False)

        bundle.delete()
        PapersPrinted.set_papers_printed(False)
