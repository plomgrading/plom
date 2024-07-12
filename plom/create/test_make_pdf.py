# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022, 2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from pathlib import Path

from pytest import raises
import fitz

from plom.create.demotools import buildDemoSourceFiles
from plom.create.mergeAndCodePages import make_PDF
from plom import SpecVerifier


def test_make_pdf_non_ascii_stuff(tmp_path) -> None:
    tmp_path = Path("/home/cbm/src/plom/plom.git/t1")
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
    tmp_path = Path("/home/cbm/src/plom/plom.git/t1")
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
    size1 = pdf1.stat().st_size
    size2 = pdf2.stat().st_size
    assert size2 >= size1
    assert size2 < 2.0 * size1
