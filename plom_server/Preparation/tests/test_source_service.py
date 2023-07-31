# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from django.test import TestCase
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from model_bakery import baker

from ..services import TestSourceService
from ..models import PaperSourcePDF
from .. import useful_files_for_testing as useful_files


class SourceServiceTests(TestCase):
    def test_store_source(self):
        """Test TestSourceService.store_test_source()."""
        tss = TestSourceService()
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        # TODO: this writes to settings.MEDIA_ROOT
        # TODO: would one normally use a special "tests" settings?
        tss.store_test_source(1, upload_path)

        n_sources = len(PaperSourcePDF.objects.all())
        self.assertEqual(n_sources, 1)

        pdf_save_path = settings.MEDIA_ROOT / "sourceVersions" / "version1.pdf"
        self.assertTrue(pdf_save_path.exists())

        with self.assertRaises(MultipleObjectsReturned):
            tss.store_test_source(1, upload_path)

    def test_check_duplicates(self):
        """Test TestSourceService.check_pdf_duplication()."""
        tss = TestSourceService()
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        version_1 = baker.make(PaperSourcePDF, version=1, hash="abcde123")
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        version_2 = baker.make(PaperSourcePDF, version=2, hash="abcde123")
        duplicates = tss.check_pdf_duplication()
        self.assertEqual(duplicates, {"abcde123": [1, 2]})
