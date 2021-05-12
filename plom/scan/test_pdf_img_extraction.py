# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pathlib import Path

from pytest import raises
import fitz
from PIL import Image

from plom import ScenePixelHeight
from plom.scan.scansToImages import processFileToBitmaps


def test_pdf_extract_img_height(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page()
    d.save(f)
    processFileToBitmaps(f, tmp_path)
    im = Image.open(tmp_path / "doc-1.png")
    assert im.height == ScenePixelHeight


def test_pdf_extract_img_heights_other(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page(width=500, height=842)
    d.new_page(width=100, height=100)
    d.new_page(width=100, height=842)
    d.new_page(width=400, height=100)
    d.save(f)
    processFileToBitmaps(f, tmp_path)
    im = Image.open(tmp_path / "doc-1.png")
    assert im.height == ScenePixelHeight
    im = Image.open(tmp_path / "doc-2.png")
    assert im.height == ScenePixelHeight
    assert im.width == ScenePixelHeight
    im = Image.open(tmp_path / "doc-3.png")
    assert im.height > ScenePixelHeight
    im = Image.open(tmp_path / "doc-4.png")
    assert im.height < ScenePixelHeight


def test_pdf_extract_img_ridiculous_ratios(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page(width=1, height=200)
    d.save(f)
    raises(ValueError, lambda: processFileToBitmaps(f, tmp_path))
    d = fitz.open()
    d.new_page(width=100, height=2)
    d.save(f)
    raises(ValueError, lambda: processFileToBitmaps(f, tmp_path))
