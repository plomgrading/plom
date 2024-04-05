# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
import tempfile

import fitz

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File
from django.db import transaction

from Papers.services import SpecificationService
from ..models import PaperSourcePDF


class TestSourceService:
    @transaction.atomic
    def get_source_pdf_path(self, source_version: int):
        """Return the path to the given source test version pdf.

        In practice this would instead return the URL.

        Args:
            source_version: The version of the pdf.
        """
        try:
            pdf_obj = PaperSourcePDF.objects.get(version=source_version)
            return pdf_obj.source_pdf.path
        except PaperSourcePDF.DoesNotExist:
            raise ObjectDoesNotExist(
                f"Source version {source_version} not yet uploaded"
            )

    @transaction.atomic
    def how_many_test_versions_uploaded(self) -> int:
        return PaperSourcePDF.objects.count()

    @transaction.atomic
    def are_all_test_versions_uploaded(self) -> bool:
        if SpecificationService.is_there_a_spec():
            return (
                PaperSourcePDF.objects.count() == SpecificationService.get_n_versions()
            )
        else:
            return False

    @transaction.atomic
    def get_list_of_uploaded_sources(self) -> dict[int, tuple[str, str]]:
        """Return a dict of uploaded source versions and their urls."""
        status = {}
        for pdf_obj in PaperSourcePDF.objects.all():
            status[pdf_obj.version] = (pdf_obj.source_pdf.url, pdf_obj.hash)
        return status

    def get_list_of_sources(self) -> dict[int, None | tuple[str, str]]:
        """Return a dict of all versions, uploaded or not."""
        status: dict[int, None | tuple[str, str]] = {
            v: None for v in SpecificationService.get_list_of_versions()
        }
        for pdf_obj in PaperSourcePDF.objects.all():
            status[pdf_obj.version] = (pdf_obj.source_pdf.url, pdf_obj.hash)
        return status

    @transaction.atomic
    def store_source_pdf(self, source_version: int, source_pdf: Path) -> None:
        """Store one of the source PDF files into the database.

        Args:
            source_version: which version, indexed from one.
            source_pdf: a path to an actual file.

        Returns:
            None

        Raises:
            MultipleObjectsReturned: tried to store when already present.
            ObjectDoesNotExist: TODO: unsure when this is called but some
                callers seem to think it can happen.  Consider refactoring...
        """
        try:
            PaperSourcePDF.objects.get(version=source_version)
            raise MultipleObjectsReturned(
                f"Source pdf with version {source_version} already present."
            )
        except PaperSourcePDF.DoesNotExist:
            pass

        with open(source_pdf, "rb") as fh:
            bytes = fh.read()  # read entire file as bytes
            hashed = hashlib.sha256(bytes).hexdigest()

        with open(source_pdf, "rb") as fh:
            dj_file = File(fh, name=f"version{source_version}.pdf")
            pdf_obj = PaperSourcePDF(
                version=source_version, source_pdf=dj_file, hash=hashed
            )
            pdf_obj.save()

    def take_source_from_upload(
        self, version: int, required_pages: int, in_memory_file: File
    ) -> tuple[bool, str]:
        """

        Args:
            version: which version, one-based index.
            required_pages: how many pages we expect.
                TODO: consider refactoring to ask the SpecService directly.
            in_memory_file: File-object containing the pdf
                (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
                TODO: I'm still very uncertain about the types of these, see
                also :py:`ScanService.upload_bundle`.  This one is also called by
                `Preparation/management/commands/plom_preperation_test_source.py`
                which passes a plain-old open file handle.

        Returns:
            A tuple with a boolean for success and a message or error message.
        """
        # save the file to a temp directory
        # TODO - size limits please
        with tempfile.TemporaryDirectory() as td:
            tmp_pdf = Path(td) / "unvalidated.pdf"
            with open(tmp_pdf, "wb") as fh:
                for chunk in in_memory_file:
                    fh.write(chunk)
            # now check it has correct number of pages
            doc = fitz.open(tmp_pdf)
            if doc.page_count != int(required_pages):
                return (
                    False,
                    f"Uploaded pdf has {doc.page_count} pages, but spec requires {required_pages}",
                )
            # now try to store it
            try:
                self.store_source_pdf(version, tmp_pdf)
            except (ObjectDoesNotExist, MultipleObjectsReturned) as err:
                return (False, str(err))

            return (True, "PDF successfully uploaded")

    @transaction.atomic()
    def delete_test_source(self, source_version):
        # delete the DB entry and the file
        try:
            pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
            Path(pdf_obj.source_pdf.path).unlink()
            pdf_obj.delete()
        except PaperSourcePDF.DoesNotExist:
            pass

    @transaction.atomic()
    def delete_all_test_sources(self):
        # delete the DB entry and the file
        for pdf_obj in PaperSourcePDF.objects.all():
            Path(pdf_obj.source_pdf.path).unlink()
            pdf_obj.delete()

    @transaction.atomic
    def check_pdf_duplication(self):
        hashes = defaultdict(list)
        for pdf_obj in PaperSourcePDF.objects.all():
            hashes[pdf_obj.hash].append(pdf_obj.version)
        duplicates = {}
        for hash, versions in hashes.items():
            if len(versions) > 1:
                duplicates[hash] = versions
        return duplicates

    @transaction.atomic
    def get_source_as_bytes(self, source_version):
        try:
            pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
            with pdf_obj.source_pdf.open("rb") as fh:
                return fh.read()
        except PaperSourcePDF.DoesNotExist:
            raise ValueError("Version does not exist")
