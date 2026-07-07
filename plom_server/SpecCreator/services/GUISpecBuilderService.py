# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from pathlib import Path

import base64
import tempfile

import pymupdf

from plom_server.Preparation.services import SourceService


# TODO: this function probably already exists somewhere
def extract_images_from_django_pdf(django_pdf) -> list[bytes]:
    """Extract images from a pdf file object.

    Very little checking on this. This function assumes the caller
    isn't submitting anything too large.

    Args:
        django_pdf: a pdf file object.

    Returns:
        A list of bytes. Each item is the bytes of a png file of each
        page in the Django file.

    Raises:
        pymupdf.FileDataError: the file can't be opened as a .pdf
    """
    page_images: list[bytes] = []
    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "unvalidated.pdf"
        # write the django pdf to a tempfile
        with open(tmp_pdf, "wb") as fh:
            for chunk in django_pdf:
                fh.write(chunk)
        # do whatever we need to do
        with pymupdf.open(tmp_pdf) as doc:
            for page in doc:
                page_images.append(page.get_pixmap().tobytes())

    return page_images


def get_source_file_images_as_base64_str(version: int) -> list[str]:
    djangofile_list = SourceService.get_reference_images_as_list(version)
    b64_image_list = []
    for abstract_django_file in djangofile_list:
        print(abstract_django_file)
        with abstract_django_file.open("rb") as f:
            f.seek(0)
            image_bytes = f.read()
        b64_bytes = base64.b64encode(image_bytes).decode("ascii")
        b64_image_list.append(b64_bytes)
    return b64_image_list


def convert_png_bytes_to_base64_str(png_bytes: bytes) -> str:
    """Convert png bytes to a base64 string.

    Not unique to Django, but this util is helpful when building
    context for Django templates.
    """
    return base64.b64encode(png_bytes).decode("ascii")
