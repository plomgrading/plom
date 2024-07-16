# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022, 2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from pathlib import Path

from pytest import raises
import fitz

from plom.create.demotools import buildDemoSourceFiles
from plom.create.mergeAndCodePages import pdf_page_add_labels_QRs, create_QR_codes
from plom.create.mergeAndCodePages import make_PDF
from plom.scan import QRextract_legacy
from plom.scan import processFileToBitmaps
from plom import SpecVerifier


def test_staple_marker_diagname_very_long(tmp_path) -> None:
    assert buildDemoSourceFiles(basedir=tmp_path)
    with fitz.open(tmp_path / "sourceVersions/version1.pdf") as d:
        pdf_page_add_labels_QRs(d[0], "Mg " * 7, "bar", [])
        # d.save("debug_staple_position.pdf")  # uncomment for debugging
        with raises(AssertionError):
            pdf_page_add_labels_QRs(d[0], "Mg " * 32, "bar", [], odd=False)
            # but no error if we're not drawing staple corners
            pdf_page_add_labels_QRs(d[0], "Mg " * 32, "bar", [], odd=None)


# TODO: faster to use a Class with setup and teardown to build the PDF
def test_stamp_too_long(tmp_path) -> None:
    assert buildDemoSourceFiles(basedir=tmp_path)
    with fitz.open(tmp_path / "sourceVersions/version1.pdf") as d:
        pdf_page_add_labels_QRs(d[0], "foo", "1234 Q33 p. 38", [])
        with raises(AssertionError):
            pdf_page_add_labels_QRs(d[0], "foo", "12345 " * 20, [])


def test_stamp_QRs(tmp_path) -> None:
    assert buildDemoSourceFiles(basedir=tmp_path)
    with fitz.open(tmp_path / "sourceVersions/version1.pdf") as d:
        p = 3
        qr = create_QR_codes(6, p, 1, "12345", tmp_path)
        assert len(qr) == 4
        for q in qr:
            assert isinstance(q, Path)
        # 4 distinct QR codes
        assert len(set(qr)) == 4

        # QR list too short to place on page
        with raises(IndexError):
            pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr[:3])

        # place them on the page
        pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr, odd=bool(p % 2))

        p = 4
        qr2 = create_QR_codes(6, p, 1, "12345", tmp_path)
        # QR codes are different for the new page
        for k in range(4):
            assert qr[k] != qr2[k]
        pdf_page_add_labels_QRs(
            d[p - 1], "foo", f"0006 Q1 p. {p}", qr2, odd=bool(p % 2)
        )

        out = tmp_path / "debug_QR_codes.pdf"
        d.save(out)

    # Now let's try to read it back, some overlap with test_qr_reads
    files = processFileToBitmaps(out, tmp_path)

    d = QRextract_legacy(files[0], write_to_file=False)
    assert d is not None
    for k, v in d.items():
        print(k)
        print(v)
        assert len(v) == 0

    d = QRextract_legacy(files[2], write_to_file=False)
    assert d is not None
    assert not d["NW"]
    assert d["NE"] == ["00006003001112345"]
    assert d["SW"] == ["00006003001312345"]
    assert d["SE"] == ["00006003001412345"]

    d = QRextract_legacy(files[3], write_to_file=False)
    assert d is not None
    assert not d["NE"]
    assert d["NW"] == ["00006004001212345"]
    assert d["SW"] == ["00006004001312345"]
    assert d["SE"] == ["00006004001412345"]


def test_qr_stamp_all_pages(tmp_path) -> None:
    assert buildDemoSourceFiles(basedir=tmp_path)
    spec = SpecVerifier.demo()
    spec.checkCodes()
    pdf_path = make_PDF(
        spec,
        5,
        {1: 1, 2: 1, 3: 2},
        where=tmp_path,
        source_versions_path=(tmp_path / "sourceVersions"),
    )
    with fitz.open(pdf_path) as doc:
        # each page has three images: will break if we add images to the demo
        for p in doc.pages():
            assert len(p.get_images()) == 3
