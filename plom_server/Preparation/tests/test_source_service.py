# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald

import pathlib
from importlib import resources

from django.test import TestCase
from django.conf import settings
from model_bakery import baker

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

        # TODO: mypy complains about Traversable, in Python 3.11, remove when
        # we drop support for Python 3.10, and similar throughout this file
        SourceService.store_source_pdf(1, ver1pdf)  # type: ignore[arg-type]
        d = SourceService.get_list_of_sources()
        v1, v2 = d
        assert v1["uploaded"]
        assert not v2["uploaded"]

        SourceService.store_source_pdf(2, ver2pdf)  # type: ignore[arg-type]
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

    @config_test({"test_spec": "demo"})
    def test_store_source_pdfs_checks(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        pdf = resources.files(useful_files) / "test_version1.pdf"
        with pdf.open("rb") as f:
            r, msg = SourceService.take_source_from_upload(1, f)
        assert r
        assert "uploaded" in msg
        assert "success" in msg
        # TODO: does this make files or not?
        # SourceService.delete_source_pdf(1)

    @config_test({"test_spec": "demo"})
    def test_store_source_pdfs_out_of_range(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        pdf = resources.files(useful_files) / "test_version1.pdf"
        with pdf.open("rb") as f:
            r, msg = SourceService.take_source_from_upload(0, f)
            assert not r
            assert "range" in msg
        with pdf.open("rb") as f:
            r, msg = SourceService.take_source_from_upload(3, f)
            assert not r
            assert "range" in msg

    @config_test({"test_spec": "tiny_spec.toml"})
    def test_store_source_pdfs_wrong_page_count(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        # tiny_spec has 3 pages but the pdf here has 6
        pdf = resources.files(useful_files) / "test_version1.pdf"
        with pdf.open("rb") as f:
            r, msg = SourceService.take_source_from_upload(1, f)
        assert not r
        assert "pages" in msg

    @config_test({"test_spec": "demo"})
    def test_store_source_pdf_location(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        SourceService.store_source_pdf(1, upload_path)  # type: ignore[arg-type]
        f = SourceService._get_source_file(1)
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
        SourceService.store_source_pdf(1, upload_path)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            SourceService.store_source_pdf(1, upload_path)  # type: ignore[arg-type]
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
        SourceService.store_source_pdf(1, upload_path)  # type: ignore[arg-type]
        d = SourceService.get_list_of_sources()
        assert len(d[0]["hash"]) > 50
        SourceService.delete_source_pdf(1)

    @config_test({"test_spec": "demo"})
    def test_get_as_bytes(self) -> None:
        # we explicitly **unset** papers-printed for testing purposes
        PapersPrinted.set_papers_printed(False, ignore_dependencies=True)

        upload_path = resources.files(useful_files) / "test_version1.pdf"
        original_bytes = upload_path.read_bytes()
        SourceService.store_source_pdf(1, upload_path)  # type: ignore[arg-type]
        stored_bytes = SourceService.get_source_as_bytes(1)
        self.assertEqual(original_bytes, stored_bytes)
        with self.assertRaises(ValueError):
            SourceService.get_source_as_bytes(2)
        SourceService.delete_source_pdf(1)

    def test_source_check_duplicates(self) -> None:
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=1, hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {})

        baker.make(PaperSourcePDF, version=2, hash="abcde123")
        duplicates = SourceService.check_pdf_duplication()
        self.assertEqual(duplicates, {"abcde123": [1, 2]})
