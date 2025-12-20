# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import math
from pathlib import Path

import pymupdf

from plom.misc_utils import working_directory
from .build_extra_page_with_qrcodes import build_extra_page_pdf


def test_extra_page_pdf_no_dir(tmpdir) -> None:
    """Builds the extra_page pdf with no directory specified and confirms it works."""
    with working_directory(tmpdir):
        build_extra_page_pdf()
        assert Path("extra_page.pdf").exists()


def test_extra_page_pdf_with_dir(tmpdir) -> None:
    """Builds the extra_page pdf with a directory specified and confirms it works."""
    path_foo = Path(tmpdir) / "Foo"
    path_foo.mkdir()
    build_extra_page_pdf(destination_dir=path_foo)
    assert (path_foo / "extra_page.pdf").exists()


def test_extra_page_pdf_has_two_pages(tmpdir) -> None:
    f = build_extra_page_pdf(destination_dir=tmpdir)
    with pymupdf.open(f) as doc:
        assert len(doc) == 2


def test_extra_page_pdf_papersize(tmpdir) -> None:

    def relative_error(x, y):
        return math.fabs((x - y) / (1.0 * y))

    for papersize in ("a4", "letter", "legal"):
        latexpapersize = papersize + "paper"
        f = build_extra_page_pdf(destination_dir=tmpdir, papersize=latexpapersize)
        w_pts, h_pts = pymupdf.paper_size(papersize)
        with pymupdf.open(f) as doc:
            for p in doc:
                # print((papersize, p.rect, w_pts, h_pts))
                assert relative_error(p.rect.width, w_pts) < 0.01
                assert relative_error(p.rect.height, h_pts) < 0.01
                # (relative error b/c a4 paper from latex not integer number of points)
