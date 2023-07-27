# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
from typing import List

import fitz

from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings

from .. import models


class ReferencePDFService:
    """Keep track of the reference PDF."""

    def is_there_a_reference_pdf(self) -> bool:
        """Return True if the user has uploaded a reference PDF already."""
        return models.ReferencePDF.objects.exists()

    def create_pdf(self, slug: str, pages: int, pdf) -> models.ReferencePDF:
        """Create a PDF in the database and save the file on disk.

        Args:
            slug: url-safe filename (w/o extension)
            pages: number of pages in the pdf
            pdf: in-memory PDF file

        Returns:
            models.ReferencePDF: the reference PDF object
        """
        pdf_path = settings.MEDIA_ROOT / "spec_reference.pdf"
        pdf_path.unlink(missing_ok=True)

        pdf = models.ReferencePDF(filename_slug=slug, num_pages=pages, pdf=pdf)
        pdf.save()
        return pdf

    def delete_pdf(self):
        """Clear the ReferencePDF table."""
        pdfs = models.ReferencePDF.objects.all()
        pdfs.delete()

    def new_pdf(self, spec_service, slug, pages, file_bytes):
        """Create and save a new PDF given an opened file."""
        self.delete_pdf()
        spec_service.clear_questions()  # clear questions from the test specification
        pdf = self.create_pdf(slug, pages, file_bytes)
        self.get_and_save_pdf_images()
        spec_service.set_pages(pdf.num_pages)

        return pdf

    def get_pdf(self):
        """Get the reference PDF.

        Raises:
            RuntimeError: if there is no PDF uploaded yet.
            MultipleObjectsReturned: if there is more than one Reference PDF saved to the database

        Returns:
            models.ReferencePDF: PDF object
        """
        pdfs = models.ReferencePDF.objects.all()
        if len(pdfs) == 0:
            raise RuntimeError("No Reference PDF found.")
        if len(pdfs) > 1:
            raise MultipleObjectsReturned("More than one Reference PDF saved.")

        return pdfs[0]

    def get_and_save_pdf_images(self) -> None:
        """Get raster image of each PDF page, and save them to disk for displaying.

        Raises:
            RuntimeError: if the ReferencePDF's path doesn't point to a PDF
        """
        pdf = self.get_pdf()
        slug = pdf.filename_slug
        pathname = settings.MEDIA_ROOT / "spec_reference.pdf"
        if pathname.exists():
            pdf_doc = fitz.Document(pathname)

            thumbnail_dir = pathlib.Path("static") / "SpecCreator" / "thumbnails"
            if not thumbnail_dir.exists():
                thumbnail_dir.mkdir()

            slug_dir = thumbnail_dir / "spec_reference"
            if not slug_dir.exists():
                slug_dir.mkdir()

            for i in range(pdf_doc.page_count):
                page_pixmap = pdf_doc[i].get_pixmap()
                save_path = slug_dir / f"thumbnail{i}.png"
                page_pixmap.save(save_path)

        else:
            raise RuntimeError(f"Document at {pathname} does not exist.")

    def create_page_thumbnail_list(self) -> List[pathlib.Path]:
        """Create list of image paths to send to frontend for pdf thumbnail rendering.

        Returns:
            list: page thumbnail paths
        """
        pdf = self.get_pdf()
        pages = []
        thumbnail_folder = pathlib.Path("SpecCreator") / "thumbnails" / "spec_reference"
        for i in range(pdf.num_pages):
            thumbnail = thumbnail_folder / f"thumbnail{i}.png"
            pages.append(thumbnail)

        return pages
