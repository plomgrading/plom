# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

import pathlib
from importlib import resources

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from model_bakery import baker

from plom_server.Papers.services import SpecificationService
from plom_server.TestingSupport.utils import config_test
from ..services import SourceService, PapersPrinted
from ..models import PaperSourcePDF
from .. import useful_files_for_testing as useful_files


class SourceServiceTests(TestCase):
    @config_test({"test_spec": "demo"})
    def test_store_and_list_source_pdfs(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        ver1pdf = resources.files(useful_files) / "test_version1.pdf"
        ver2pdf = resources.files(useful_files) / "test_version2.pdf"

        d = SourceService.get_list_of_sources()
        assert isinstance(d, list)
        v1, v2 = d
        assert v1["version"] == 1
        assert v2["version"] == 2
        for src in d:
            assert not src["uploaded"]

        SourceService.store_source_pdf(1, ver1pdf)
        d = SourceService.get_list_of_sources()
        v1, v2 = d
        assert v1["uploaded"]
        assert not v2["uploaded"]

        SourceService.store_source_pdf(2, ver2pdf)
        d = SourceService.get_list_of_sources()
        v1, v2 = d
        assert v1["uploaded"]
        assert v2["uploaded"]

        SourceService.delete_source_pdf(1)
        d = SourceService.get_list_of_sources()
        v1, v2 = d
        assert not v1["uploaded"]
        assert v2["uploaded"]
        n_sources = SourceService.how_many_source_versions_uploaded()
        self.assertEqual(n_sources, 1)

        SourceService.delete_all_source_pdfs()
        d = SourceService.get_list_of_sources()
        for src in d:
            assert not src["uploaded"]
        n_sources = SourceService.how_many_source_versions_uploaded()
        self.assertEqual(n_sources, 0)

    def test_list_source_pdfs_without_spec(self) -> None:
        """The source list should always include version 1."""
        # notice that we haven't uploaded a spec for this test
        source_list = SourceService.get_list_of_sources()
        self.assertEqual(1, len(source_list))
        self.assertEqual(1, source_list[0]["version"])
        self.assertFalse(source_list[0]["uploaded"])

    @config_test({"test_spec": "demo"})
    def test_store_source_pdfs_checks(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        pdf = resources.files(useful_files) / "test_version1.pdf"
        with pdf.open("rb") as f:
            # using f directly will fail - f.name includes path elements
            django_file = SimpleUploadedFile(
                name="test_version1.pdf",
                content=f.read(),
                content_type="application/pdf",
            )
            SourceService.take_source_from_upload(1, django_file)

    @config_test({"test_spec": "demo"})
    def test_store_source_pdfs_validate_filename(self) -> None:
        """Check that files with suspicious names are caught."""
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        pdf = resources.files(useful_files) / "test_version1.pdf"
        with self.assertRaisesRegex(ValueError, "name.*suspicious.*path"):
            with pdf.open("rb") as f:
                SourceService.take_source_from_upload(1, f)

    @config_test({"test_spec": "demo"})
    def test_store_source_pdfs_out_of_range(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        minver = min(SpecificationService.get_list_of_versions())
        maxver = max(SpecificationService.get_list_of_versions())
        pdf = resources.files(useful_files) / "test_version1.pdf"
        with self.assertRaisesRegex(ValueError, "range"):
            with pdf.open("rb") as f:
                SourceService.take_source_from_upload(minver - 1, f)
        with self.assertRaisesRegex(ValueError, "range"):
            with pdf.open("rb") as f:
                SourceService.take_source_from_upload(maxver + 1, f)

    @config_test({"test_spec": "tiny_spec.toml"})
    def test_store_source_pdfs_wrong_page_count(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        # tiny_spec has 3 pages but the pdf here has 6
        pdf = resources.files(useful_files) / "test_version1.pdf"
        with self.assertRaisesRegex(ValueError, "pages"):
            with pdf.open("rb") as f:
                SourceService.take_source_from_upload(1, f)

    @config_test({"test_spec": "demo"})
    def test_store_source_pdf_location(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        __, f = SourceService._get_source_file(1)
        pdf_source_path = settings.MEDIA_ROOT / "sourceVersions"
        self.assertTrue(pdf_source_path.exists())
        location_on_disc = pathlib.Path(f.path).parent
        self.assertTrue(location_on_disc.resolve() == pdf_source_path.resolve())
        # This test is sus: DB might store as version1_abc123.pdf
        # assert f.path == pdf_source_path / "version1.pdf"
        SourceService.delete_source_pdf(1)

    @config_test({"test_spec": "demo"})
    def test_store_source_pdf_already_there(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        with self.assertRaisesRegex(ValueError, "already present"):
            SourceService.store_source_pdf(1, upload_path)
        n_sources = SourceService.how_many_source_versions_uploaded()
        self.assertEqual(n_sources, 1)
        SourceService.delete_source_pdf(1)

    # def test_delete_non_existing_source_pdf(self) -> None:
    #     # explicitly **unset** papers-printed for testing purposes
    #     PapersPrinted.set_papers_printed(False, ignore_dependencies=True)
    #     # documented as a non-error
    #     SourceService.delete_source_pdf(1)

    @config_test({"test_spec": "demo"})
    def test_source_pdf_list_has_hash(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)
        d = SourceService.get_list_of_sources()
        assert len(d[0]["hash"]) > 50
        SourceService.delete_source_pdf(1)

    @config_test({"test_spec": "demo"})
    def test_get_as_bytes(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        original_bytes = upload_path.read_bytes()
        SourceService.store_source_pdf(1, upload_path)
        stored_bytes = SourceService.get_source_as_bytes(1)
        self.assertEqual(original_bytes, stored_bytes)
        with self.assertRaises(ValueError):
            SourceService.get_source_as_bytes(2)
        SourceService.delete_source_pdf(1)

    def test_upload_source_version1_in_range_before_spec(self) -> None:
        """If there's no spec, source version 1 should be upload-able."""
        pdf = resources.files(useful_files) / "test_version1.pdf"
        with pdf.open("rb") as f:
            # using f directly will fail - f.name includes path elements
            django_file = SimpleUploadedFile(
                name="test_version1.pdf",
                content=f.read(),
                content_type="application/pdf",
            )
            SourceService.take_source_from_upload(1, django_file)
        source_info = SourceService.get_source_info(1)
        self.assertTrue(source_info["uploaded"])

    def test_upload_source_version2_out_of_range_before_spec(self) -> None:
        """If there's no spec, source version 2 shouldn't be upload-able."""
        pdf = resources.files(useful_files) / "test_version2.pdf"
        with pdf.open("rb") as f:
            # using f directly will fail - f.name includes path elements
            django_file = SimpleUploadedFile(
                name="test_version1.pdf",
                content=f.read(),
                content_type="application/pdf",
            )
            with self.assertRaisesRegex(ValueError, "out of range"):
                SourceService.take_source_from_upload(2, django_file)
        source_info = SourceService.get_source_info(2)
        self.assertFalse(source_info["uploaded"])

    def test_upload_source_odd_pages_fails(self) -> None:
        """The server shouldn't accept source with an odd page count."""
        pdf = resources.files(useful_files) / "test_version1_5pages.pdf"
        with pdf.open("rb") as f:
            # using f directly will fail - f.name includes path elements
            django_file = SimpleUploadedFile(
                name="test_version1_5pages.pdf",
                content=f.read(),
                content_type="application/pdf",
            )
            with self.assertRaisesRegex(ValueError, "must have an even"):
                SourceService.take_source_from_upload(1, django_file)

    def test_source_check_duplicates(self) -> None:
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=1, pdf_hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=2, pdf_hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {"abcde123": [1, 2]})
