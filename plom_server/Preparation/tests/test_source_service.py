# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

import pathlib
import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from django.test import TestCase
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from model_bakery import baker

from ..services import SourceService
from ..models import PaperSourcePDF
from .. import useful_files_for_testing as useful_files


class SourceServiceTests(TestCase):
    def test_store_source_pdf(self) -> None:
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        # TODO: this writes to settings.MEDIA_ROOT
        # TODO: would one normally use a special "tests" settings?
        SourceService.store_source_pdf(1, upload_path)

        n_sources = SourceService.how_many_source_versions_uploaded()
        self.assertEqual(n_sources, 1)

        with self.assertRaises(MultipleObjectsReturned):
            SourceService.store_source_pdf(1, upload_path)

        SourceService.delete_all_source_pdfs()
        n_sources = SourceService.how_many_source_versions_uploaded()
        self.assertEqual(n_sources, 0)

    def test_store_source_pdf_location(self) -> None:
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        f = SourceService._get_source_file(1)
        pdf_source_path = settings.MEDIA_ROOT / "sourceVersions"
        self.assertTrue(pdf_source_path.exists())
        location_on_disc = pathlib.Path(f.path).parent
        self.assertTrue(location_on_disc == pdf_source_path)
        # This test is sus: DB might store as version1_abc123.pdf
        # assert f.path == pdf_source_path / "version1.pdf"

    def test_delete_existing_source_pdf_by_version(self) -> None:
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        SourceService.delete_source_pdf(1)
        self.assertEqual(SourceService.how_many_source_versions_uploaded(), 0)

    def test_delete_non_existing_source_pdf(self) -> None:
        # documented as a non-error
        SourceService.delete_source_pdf(1)

    def test_source_pdf_misc(self) -> None:
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        d = SourceService.get_list_of_sources()
        assert isinstance(d, list)
        assert len(d) >= 1
        assert isinstance(d[0], dict)
        assert d[0]["version"] == 1
        assert len(d[0]["hash"]) > 50

    def test_get_as_bytes(self) -> None:
        upload_path = resources.files(useful_files) / "test_version1.pdf"
        original_bytes = upload_path.read_bytes()
        SourceService.store_source_pdf(1, upload_path)
        stored_bytes = SourceService.get_source_as_bytes(1)
        self.assertEqual(original_bytes, stored_bytes)
        with self.assertRaises(ValueError):
            SourceService.get_source_as_bytes(2)

    def test_source_check_duplicates(self) -> None:
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=1, hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=2, hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {"abcde123": [1, 2]})
