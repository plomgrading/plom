# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

from pathlib import Path

import base64
import tempfile

import pymupdf


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


def convert_png_bytes_to_base64_str(png_bytes: bytes) -> str:
    """Convert png bytes to a base64 string.

    Not unique to Django, but this util is helpful when building
    context for Django templates.
    """
    return base64.b64encode(png_bytes).decode("ascii")
