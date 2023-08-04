# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Julian Lapenna

from pathlib import Path

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from ..services import TestSpecService, ReferencePDFService
from .. import models


class TestSpecRefPDFTests(TestCase):
    """Tests services code for models.ReferencePDF."""

    @classmethod
    def setUpClass(cls):
        """Init a dummy pdf file."""
        cls.dummy_file = SimpleUploadedFile(
            "dummy.pdf", b"Test text", content_type="application/pdf"
        )
        return super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Remove all saved dummy files from disk."""
        # TODO: I guess the on delete signal doesn't get called when running tests?
        media_path = Path("SpecCreator/media")
        for f in media_path.iterdir():
            f.unlink()
        return super().tearDownClass()

    def test_create_refpdf(self):
        """Test `services.create_pdf`."""
        spec = TestSpecService()
        ref_service = ReferencePDFService(spec)
        new_pdf = ref_service.create_pdf("dummy", 1, self.dummy_file)
        self.assertEqual(new_pdf.filename_slug, "dummy")
        self.assertEqual(new_pdf.num_pages, 1)

    def test_delete_refpdf(self):
        """Test `services.delete_pdf`."""
        spec = TestSpecService()
        ref_service = ReferencePDFService(spec)
        new_pdf = ref_service.create_pdf("dummy", 1, self.dummy_file)
        num_pdfs = models.ReferencePDF.objects.all().count()
        self.assertEqual(num_pdfs, 1)
        ref_service.delete_pdf()
        num_pdfs = models.ReferencePDF.objects.all().count()
        self.assertEqual(num_pdfs, 0)
