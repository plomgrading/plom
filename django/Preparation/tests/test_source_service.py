# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import shutil

from django.test import TestCase
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from model_bakery import baker

from Preparation.services import TestSourceService
from Preparation.models import PaperSourcePDF


class SourceServiceTests(TestCase):
    def tearDown(self):
        source_versions_path = settings.BASE_DIR / "sourceVersions"
        if source_versions_path.exists():
            shutil.rmtree(source_versions_path)
        return super().tearDown()

    def test_store_source(self):
        """
        Test TestSourceService.store_test_source()
        """
        tss = TestSourceService()
        upload_path = (
            settings.BASE_DIR / "useful_files_for_testing" / "test_version1.pdf"
        )
        tss.store_test_source(1, upload_path)

        n_sources = len(PaperSourcePDF.objects.all())
        self.assertEqual(n_sources, 1)

        pdf_save_path = settings.BASE_DIR / "media" / "sourceVersions" / "version1.pdf"
        self.assertTrue(pdf_save_path.exists())

        with self.assertRaises(MultipleObjectsReturned):
            tss.store_test_source(1, upload_path)

    def test_check_duplicates(self):
        """
        Test TestSourceService.check_pdf_duplication()
        """
        tss = TestSourceService()
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        version_1 = baker.make(PaperSourcePDF, version=1, hash="abcde123")
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        version_2 = baker.make(PaperSourcePDF, version=2, hash="abcde123")
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {"abcde123": [1, 2]})
