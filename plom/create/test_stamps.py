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
    pdf_page_add_labels_QRs(d[0], "Mg " * 7, "bar", [], odd=True)
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
    pdf_page_add_labels_QRs(d[0], "foo", "1234 Q33 p. 38", [], odd=True)
    with raises(AssertionError):
        pdf_page_add_labels_QRs(d[0], "foo", "MMMM " * 5, [], odd=True)
    d.close()


def test_stamp_QRs(tmpdir):
    tmpdir = Path(tmpdir)
    assert buildDemoSourceFiles(basedir=tmpdir)
    d = fitz.open(tmpdir / "sourceVersions/version1.pdf")
    p = 3
    qr = create_QR_codes(6, p, 2, "123456", tmpdir)
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr, odd=(p % 2))
    p = 4
    qr = create_QR_codes(6, p, 2, "123456", tmpdir)
    pdf_page_add_labels_QRs(d[p - 1], "foo", f"0006 Q1 p. {p}", qr, odd=(p % 2))
    # d.save("debug_QR_codes.pdf")  # uncomment for debugging
