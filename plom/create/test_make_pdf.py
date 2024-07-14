# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022, 2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

import fitz

from plom.create.demotools import buildDemoSourceFiles
from plom.create.mergeAndCodePages import make_PDF
from plom import SpecVerifier


def test_make_pdf_non_ascii_stuff(tmp_path) -> None:
    assert buildDemoSourceFiles(basedir=tmp_path)
    r = SpecVerifier.demo().spec
    r["name"] = "시험"
    r["question"]["1"]["label"] = "강남스타일"
    spec = SpecVerifier(r)
    spec.checkCodes()
    pdf_path = make_PDF(
        spec,
        6,
        {1: 1, 2: 1, 3: 2},
        extra={"name": "싸이", "id": "12345678"},
        no_qr=False,
        fakepdf=False,
        xcoord=None,
        ycoord=None,
        where=tmp_path,
        source_versions_path=(tmp_path / "sourceVersions"),
    )
    with fitz.open(pdf_path) as doc:
        assert len(doc) == spec["numberOfPages"]


def test_make_pdf_non_ascii_names_font_subsetting(tmp_path) -> None:
    """Because of PyMuPDF's font subsetting, non-ascii names should not blowup the filesize."""
    assert buildDemoSourceFiles(basedir=tmp_path)
    spec = SpecVerifier.demo()
    spec.checkCodes()
    pdf1 = make_PDF(
        spec,
        5,
        {1: 1, 2: 1, 3: 2},
        extra={"name": "Bore Ring Ascii", "id": "87654321"},
        no_qr=False,
        fakepdf=False,
        xcoord=None,
        ycoord=None,
        where=tmp_path,
        source_versions_path=(tmp_path / "sourceVersions"),
    )
    pdf2 = make_PDF(
        spec,
        6,
        {1: 1, 2: 1, 3: 2},
        extra={"name": "싸이", "id": "12345678"},
        no_qr=False,
        fakepdf=False,
        xcoord=None,
        ycoord=None,
        where=tmp_path,
        source_versions_path=(tmp_path / "sourceVersions"),
    )
    assert pdf1
    assert pdf2
    size1 = pdf1.stat().st_size
    size2 = pdf2.stat().st_size
    # fallback font is subsetted so don't expect much increase
    assert size2 < 1.5 * size1
    # didn't expect it to get smaller, although sometimes it does!
    assert size2 > 0.9 * size1
