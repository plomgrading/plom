# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from collections import defaultdict
import hashlib
import pathlib
from pathlib import Path
import tempfile
from typing import Any

import fitz

from django.core.files import File
from django.db import transaction

from Papers.services import SpecificationService
from ..models import PaperSourcePDF


def _get_source_file(source_version: int) -> File:
    """Return the Django-file for a specified source version.

    Args:
        source_version: which source version.

    Returns:
        Some sort of file abstraction, not for use outside Django.

    Raises:
        ObjectDoesNotExist: not yet uploaded or out of range.
    """
    return PaperSourcePDF.objects.get(version=source_version).source_pdf


@transaction.atomic
def how_many_source_versions_uploaded() -> int:
    return PaperSourcePDF.objects.count()


@transaction.atomic
def are_all_sources_uploaded() -> bool:
    if SpecificationService.is_there_a_spec():
        return PaperSourcePDF.objects.count() == SpecificationService.get_n_versions()
    else:
        return False


@transaction.atomic()
def delete_source_pdf(source_version: int) -> None:
    """Delete a particular version of the source PDF files.

    If no such version exists (either out of range or never uploaded)
    then silently return (no error is raised).
    """
    # delete the DB entry and the file
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
        Path(pdf_obj.source_pdf.path).unlink()
        pdf_obj.delete()
    except PaperSourcePDF.DoesNotExist:
        pass


@transaction.atomic()
def delete_all_source_pdfs() -> None:
    """Delete all versions of the source PDF files."""
    # delete the DB entry and the file
    for pdf_obj in PaperSourcePDF.objects.all():
        Path(pdf_obj.source_pdf.path).unlink()
        pdf_obj.delete()


@transaction.atomic
def get_list_of_sources() -> list[dict[str, Any]]:
    """Return a list of sources, indicating if each is uploaded or not along with other info.

    The list is sorted by the version.
    """
    status = [
        {"version": v, "uploaded": False}
        for v in SpecificationService.get_list_of_versions()
    ]
    for pdf_obj in PaperSourcePDF.objects.all():
        # TODO: not super happy about explicit indexing into this list
        item = {
            "version": pdf_obj.version,
            "uploaded": True,
            "hash": pdf_obj.hash,
        }
        # TODO: what should happen if there is no spec?  above is empty...
        # We hit this in testing...
        try:
            status[pdf_obj.version - 1] = item
        except IndexError:
            # TODO: surely not the right fix if index is meaningful!
            status.append(item)
    return status


@transaction.atomic
def store_source_pdf(version: int, source_pdf: pathlib.Path) -> None:
    """Store one of the source PDF files into the database.

    This does little error checked; its perhaps intended for internal use.

    Args:
        source_version: which version, indexed from one.
        source_pdf: a path to an actual file.

    Returns:
        None

    Raises:
        ValueError: source already present for that version.
    """
    try:
        PaperSourcePDF.objects.get(version=version)
    except PaperSourcePDF.DoesNotExist:
        pass
    else:
        raise ValueError(f"Source pdf with version {version} already present.")

    with open(source_pdf, "rb") as fh:
        the_bytes = fh.read()  # read entire file as bytes
        hashed = hashlib.sha256(the_bytes).hexdigest()

    with open(source_pdf, "rb") as fh:
        dj_file = File(fh, name=f"version{version}.pdf")
        PaperSourcePDF.objects.create(version=version, source_pdf=dj_file, hash=hashed)


def take_source_from_upload(version: int, in_memory_file: File) -> tuple[bool, str]:
    """Store a PDF file as one of the source versions, after doing some checks.

    Args:
        version: which version, one-based index.
        in_memory_file: File-object containing the pdf
            (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
            TODO: I'm still very uncertain about the types of these, see
            also :py:`ScanService.upload_bundle`.  This one is also called by
            `Preparation/management/commands/plom_preperation_test_source.py`
            which passes a plain-old open file handle.

    Returns:
        A tuple with a boolean for success and a message or error message.
    """
    if version not in SpecificationService.get_list_of_versions():
        return (False, f"Version {version} is out of range")
    required_pages = SpecificationService.get_n_pages()
    # save the file to a temp directory
    # TODO - size limits please
    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "unvalidated.pdf"
        with open(tmp_pdf, "wb") as fh:
            for chunk in in_memory_file:
                fh.write(chunk)
        # now check it has correct number of pages
        with fitz.open(tmp_pdf) as doc:
            if doc.page_count != int(required_pages):
                return (
                    False,
                    f"Uploaded pdf has {doc.page_count} pages, but spec requires {required_pages}",
                )
        # now try to store it
        try:
            store_source_pdf(version, tmp_pdf)
        except ValueError as err:
            return (False, str(err))

        return (True, "PDF successfully uploaded")


@transaction.atomic
def check_pdf_duplication() -> dict[str, list[int]]:
    hashes = defaultdict(list)
    for pdf_obj in PaperSourcePDF.objects.all():
        hashes[pdf_obj.hash].append(pdf_obj.version)
    duplicates = {}
    for hash, versions in hashes.items():
        if len(versions) > 1:
            duplicates[hash] = versions
    return duplicates


@transaction.atomic
def get_source_as_bytes(source_version: int) -> bytes:
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
        with pdf_obj.source_pdf.open("rb") as fh:
            return fh.read()
    except PaperSourcePDF.DoesNotExist:
        raise ValueError("Version does not exist")
