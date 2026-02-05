# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

import hashlib
import pathlib
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import pymupdf
from django.core.files import File
from django.db import transaction

from plom.scan import QRextract
from plom_server.Papers.models import ReferenceImage
from plom_server.Papers.services import SpecificationService
from plom_server.Scan.services import ScanService
from ..models import PaperSourcePDF
from ..services.mocker import ExamMockerService
from ..services.preparation_dependency_service import assert_can_modify_sources


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


def _get_source_files() -> list[File]:
    """Return the ordered list of Django-files for all current source versions.

    Returns:
        Some sort of file abstraction, not for use outside Django.
    """
    return [x.source_pdf for x in PaperSourcePDF.objects.all().order_by("version")]


@transaction.atomic
def how_many_source_versions_uploaded() -> int:
    return PaperSourcePDF.objects.count()


@transaction.atomic
def are_all_sources_uploaded() -> bool:
    if SpecificationService.is_there_a_spec():
        return PaperSourcePDF.objects.count() == SpecificationService.get_n_versions()
    else:
        return False


def delete_source_pdf(version: int) -> None:
    """Delete a particular version of the source PDF files.

    If no such version exists (either out of range or never uploaded)
    then silently return (no error is raised).

    Raises:
        PlomDependencyException: sources cannot be modified.
    """
    assert_can_modify_sources()

    with transaction.atomic(durable=True):
        # delete the DB entry and *then* the file: the order is important
        # b/c the atomic operation can undo the DB operation but not the
        # file unlinking!
        # TODO: Colin thinks this important juggling should be in the model
        # TODO: see for example Paper/models/reference_image.py
        try:
            pdf_obj = PaperSourcePDF.objects.get(version=version)
        except PaperSourcePDF.DoesNotExist:
            return
        # force QuerySet to list: we're going to traverse twice; don't want any magic
        img_objs = list(ReferenceImage.objects.filter(version=version))
        # Make sure we delete after we get the ReferenceImages (before the cascade)
        pdf_obj.delete()  # delete the db row
        # remove associated images, first by deleting their db rows
        for img_obj in img_objs:
            img_obj.delete()

    # now that we're sure the database has been updated (by the atomic durable)
    # we can safely delete the file.  If the power went out *right now*, the
    # database would be fine and we'd have a dangling file on disc.
    pdf_obj.source_pdf.delete(save=False)
    # (This looks like we're using the object after deletion but its "ok" b/c
    # pdf_obj is the Django abstraction)

    for img_obj in img_objs:
        if img_obj.image_file:
            img_obj.image_file.delete(save=False)  # delete the underlying file


def delete_all_source_pdfs() -> None:
    """Delete all versions of the source PDF files.

    Raises:
        PlomDependencyException: sources cannot be modified.
    """
    assert_can_modify_sources(deleting=True)

    for pdf_obj in PaperSourcePDF.objects.all():
        delete_source_pdf(pdf_obj.version)


def get_source(version: int) -> dict[str, Any]:
    """Return a dictionary with info about the source version.

    Args:
        version: which version, indexed from one.

    Returns:
        A dictionary with the version, uploaded status, and---if
        uploaded---the file hash and original filename.
    """
    try:
        src = PaperSourcePDF.objects.filter(version=version).get()
        duplicates_dict = check_pdf_duplication()
        duplicate_versions = []
        try:
            duplicate_versions = duplicates_dict[src.pdf_hash]
            duplicate_versions.remove(src.version)
        except KeyError:
            pass

        return {
            "version": src.version,
            "uploaded": True,
            "hash": src.pdf_hash,
            "original_filename": src.original_filename,
            "page_count": src.page_count,
            "paper_size_name": src.paper_size_name,
            "paper_size_width": src.paper_size_width,
            "paper_size_height": src.paper_size_height,
            "duplicate_versions": duplicate_versions,
        }
    except PaperSourcePDF.DoesNotExist:
        return {"version": version, "uploaded": False}


@transaction.atomic
def get_list_of_sources() -> list[dict[str, Any]]:
    """Return a list of sources, indicating if each is uploaded or not along with other info.

    The list is sorted by the version.
    """
    vers = SpecificationService.get_list_of_versions()
    return [get_source(v) for v in vers]


# TODO: mypy stumbling over Traverseable?  but abc.Traversable added in Python 3.11
# source_pdf: pathlib.Path | resources.abc.Traversable,
def store_source_pdf(
    version: int,
    source_pdf: pathlib.Path,
    *,
    original_filename: str = "",
    page_count: int | None = None,
    paper_size_name: str = "",
    paper_size_width: float | None = None,
    paper_size_height: float | None = None,
) -> None:
    """Store one of the source PDF files into the database.

    This does very little error checking; its perhaps intended for internal use.

    Args:
        version: which version, indexed from one.
        source_pdf: a path to an actual file.

    Keyword Args:
        original_filename: optionally, the the original filename of this data.
        page_count: optionally, the number of pages.
        paper_size_name: optionally, a string describing the page sizes,
            or something like "various" if the pages are of inhomogeneous
            sizes (which sounds like a bad  idea).
        paper_size_width: optionally, width of page in pts.
        paper_size_height: optionally, height of page in pts.

    Returns:
        None

    Raises:
        ValueError: source already present for that version.
        PlomDependencyException: sources cannot currently be modified.
    """
    assert_can_modify_sources()

    try:
        PaperSourcePDF.objects.get(version=version)
    except PaperSourcePDF.DoesNotExist:
        pass
    else:
        raise ValueError(f"Source pdf with version {version} already present.")

    with open(source_pdf, "rb") as fh:
        the_bytes = fh.read()  # read entire file as bytes
    hash_value = hashlib.sha256(the_bytes).hexdigest()

    with open(source_pdf, "rb") as fh:
        dj_file = File(fh, name=f"version{version}.pdf")
        PaperSourcePDF.objects.create(
            version=version,
            source_pdf=dj_file,
            pdf_hash=hash_value,
            original_filename=original_filename,
            page_count=page_count,
            paper_size_name=paper_size_name,
            paper_size_width=paper_size_width,
            paper_size_height=paper_size_height,
        )


def take_source_from_upload(version: int, in_memory_file: File) -> tuple[bool, str]:
    """Store a PDF file as one of the source versions, after doing some checks.

    Args:
        version: which version, one-based index.
        in_memory_file: File-object containing the pdf
            (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
            TODO: I'm still very uncertain about the types of these, see
            also :py:`ScanService.upload_bundle`.  This one is also called by
            `Preparation/management/commands/plom_preparation_source.py`
            which passes a plain-old open file handle, although that file
            is marked as deprecated.

    Raises:
        PlomDependencyException: if preparation dependencies prevent modification
            of source files.

    Returns:
        A tuple with a boolean for success and a message or error message,
        for example if the PDF already exists.
    """
    # raises a PlomDependencyException if cannot modify
    assert_can_modify_sources()

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
        with pymupdf.open(tmp_pdf) as doc:
            page_count = doc.page_count
            if page_count != int(required_pages):
                return (
                    False,
                    f"Uploaded pdf has {page_count} pages, but spec requires {required_pages}",
                )
            # keep the first page's size in full float precision
            w_float, h_float = doc[0].rect.width, doc[0].rect.height
            # collect all page sizes using "set" to combine any rounding to the same int
            sizes = set(
                [(round(p.rect.width), round(p.rect.height)) for p in doc.pages()]
            )
            if len(sizes) == 1:
                ((w, h),) = sizes
                paper_size_name = "custom"
                # find a name for the size in pymupdf's dict (which uses ints):
                for name, sz in pymupdf.paper_sizes().items():
                    if sz == (w, h):
                        paper_size_name = name
            else:
                paper_size_name = "various (!)"
                w_float = None
                h_float = None

        if hasattr(in_memory_file, "name"):
            original_filename = in_memory_file.name
        else:
            original_filename = ""
        # now try to store it
        try:
            store_source_pdf(
                version,
                tmp_pdf,
                original_filename=original_filename,
                page_count=page_count,
                paper_size_name=paper_size_name,
                paper_size_width=w_float,
                paper_size_height=h_float,
            )
        except ValueError as err:
            return (False, str(err))

        store_reference_images(version)

        return (True, "PDF successfully uploaded")


@transaction.atomic
def check_pdf_duplication() -> dict[str, list[int]]:
    hashes = defaultdict(list)
    for pdf_obj in PaperSourcePDF.objects.all():
        hashes[pdf_obj.pdf_hash].append(pdf_obj.version)
    duplicates = {}
    for pdf_hash, versions in hashes.items():
        if len(versions) > 1:
            duplicates[pdf_hash] = versions
    return duplicates


@transaction.atomic
def get_source_as_bytes(source_version: int) -> bytes:
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
        with pdf_obj.source_pdf.open("rb") as fh:
            return fh.read()
    except PaperSourcePDF.DoesNotExist:
        raise ValueError("Version does not exist")


@transaction.atomic
def store_reference_images(source_version: int):
    """From an uploaded source pdf create reference images of each page.

    Uses the exam mocker to put qr codes stamps in correct pages.
    Then stores the images with that qr-code information.
    """
    mock_exam_pdf_bytes = ExamMockerService.mock_exam(source_version)
    doc = pymupdf.Document(stream=mock_exam_pdf_bytes)

    with tempfile.TemporaryDirectory() as _tmpdir:
        tmpdir = pathlib.Path(_tmpdir)
        for n, pg in enumerate(doc.pages()):
            pix = pg.get_pixmap(dpi=200, annots=True)
            fname = tmpdir / f"ref_{source_version}_{n+1}.png"
            pix.save(fname)
            code_dict = QRextract(fname)
            page_data = ScanService.parse_qr_code([code_dict])
            with open(fname, "rb") as fh:
                pix_file = File(fh, name=fname.name)
                ReferenceImage.objects.create(
                    page_number=n + 1,
                    version=source_version,
                    image_file=pix_file,
                    parsed_qr=page_data,
                )


def _get_reference_image_file(source_version: int, page_number: int) -> File:
    """Return the Django-file for a specified reference image page / version.

    Args:
        source_version: which source version.
        page_number: which page

    Returns:
        Some sort of file abstraction, not for use outside Django.

    Raises:
        ObjectDoesNotExist: not yet uploaded or out of range.
    """
    return ReferenceImage.objects.get(
        version=source_version, page_number=page_number
    ).image_file
