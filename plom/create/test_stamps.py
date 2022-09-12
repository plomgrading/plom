# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path

from pytest import raises
import fitz

from plom.create.demotools import buildDemoSourceFiles
from plom.create.mergeAndCodePages import pdf_page_add_labels_QRs, create_QR_codes
from plom.create.mergeAndCodePages import create_exam_and_insert_QR
from plom.scan import QRextract
from plom.scan import processFileToBitmaps
from plom import SpecVerifier
from plom.misc_utils import working_directory


def test_staple_marker_diagname_very_long(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    pdf_page_add_labels_QRs(d[0], "Mg " * 7, "bar", [])
    # d.save("debug_staple_position.pdf")  # uncomment for debugging
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "Mg " * 32, "bar", [], odd=False)
    # but no error if we're not drawing staple corners
    pdf_page_add_labels_QRs(d[0], "Mg " * 32, "bar", [], odd=None)
    d.close()


# TODO: faster to use a Class with setup and teardown to build the PDF
def test_stamp_too_long(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    pdf_page_add_labels_QRs(d[0], "foo", "1234 Q33 p. 38", [])
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "foo", "12345 " * 20, [])
    d.close()


def test_stamp_QRs(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    p = 3
    qr = create_QR_codes(6, p, 1, "12345", tmpdir)
    assert len(qr) == 4
    for q in qr:
        assert isinstance(q, Path)
    # 4 distinct QR codes
    assert len(set(qr)) == 4

    # QR list too short to place on page
    with raises(IndexError):
        pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr[:3])

    # place them on the page
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr, odd=(p % 2))

    p = 4
    qr2 = create_QR_codes(6, p, 1, "12345", tmpdir)
    # QR codes are different for the new page
    for k in range(4):
        assert qr[k] != qr2[k]
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr2, odd=(p % 2))

    out = tmpdir / "debug_QR_codes.pdf"
    d.save(out)

    # Now let's try to read it back, some overlap with test_qr_reads
    files = processFileToBitmaps(out, tmpdir)

    p = QRextract(files[0], write_to_file=False)
    for k, v in p.items():
        print(k)
        print(v)
        assert len(v) == 0

    p = QRextract(files[2], write_to_file=False)
    assert not p["NW"]
    assert p["NE"] == ["00006003001112345"]
    assert p["SW"] == ["00006003001312345"]
    assert p["SE"] == ["00006003001412345"]

    p = QRextract(files[3], write_to_file=False)
    assert not p["NE"]
    assert p["NW"] == ["00006004001212345"]
    assert p["SW"] == ["00006004001312345"]
    assert p["SE"] == ["00006004001412345"]


def test_qr_stamp_all_pages(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    spec = SpecVerifier.demo()
    spec.checkCodes()
    with working_directory(tmpdir):
        ex = create_exam_and_insert_QR(spec, 5, {1: 1, 2: 1, 3: 2}, tmpdir)
    # each page has three images: will break if we add images to the demo
    for p in ex.pages():
        assert len(p.get_images()) == 3
