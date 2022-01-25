# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path

from pytest import raises
import fitz

from plom.create.demotools import buildDemoSourceFiles
from plom.create.mergeAndCodePages import pdf_page_add_labels_QRs, create_QR_codes


def test_staple_marker_diagname_too_long(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    pdf_page_add_labels_QRs(d[0], "Mg " * 7, "bar", [])
    # d.save("debug_staple_position.pdf")  # uncomment for debugging
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "Mg " * 8, "bar", [], odd=True)
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "Mg " * 8, "bar", [], odd=False)
    # but no error if we're not drawing staple corners
    pdf_page_add_labels_QRs(d[0], "Mg " * 8, "bar", [], odd=None)
    d.close()


# TODO: faster to use a Class with setup and teardown to build the PDF
def test_stamp_too_long(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    pdf_page_add_labels_QRs(d[0], "foo", "1234 Q33 p. 38", [])
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "foo", "MMMM MMMM MMMM MMMM 12345", [])
    d.close()


def test_stamp_QRs(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    p = 3
    qr = create_QR_codes(6, p, 1, "123456", tmpdir)
    assert len(qr) == 4
    for q in qr:
        assert isinstance(q, Path)
    # 4 distinct QR codes
    assert len(set(qr)) == 4

    # place them on the page
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr, odd=(p % 2))

    p = 4
    qr2 = create_QR_codes(6, p, 1, "123456", tmpdir)
    # QR codes are different for the new page
    for k in range(4):
        assert qr[k] != qr2[k]
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr2, odd=(p % 2))

    # QR list too short
    with raises(IndexError):
        pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr[:3])
    d.save("debug_QR_codes.pdf")  # uncomment for debugging
