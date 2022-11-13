# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

from pathlib import Path
import shutil

from pytest import raises
import fitz
from PIL import Image

from plom.misc_utils import working_directory
from plom import ScenePixelHeight
from plom.scan import processFileToBitmaps


def test_pdf_process_img_height(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page()
    d.save(f)
    processFileToBitmaps(f, tmp_path)
    im = Image.open(tmp_path / "doc-001.png")
    assert im.height == ScenePixelHeight


def test_pdf_process_img_heights_other(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page(width=500, height=842)
    d.new_page(width=100, height=100)
    d.new_page(width=100, height=842)
    d.new_page(width=400, height=100)
    d.save(f)
    processFileToBitmaps(f, tmp_path)
    im = Image.open(tmp_path / "doc-001.png")
    assert im.height == ScenePixelHeight
    im = Image.open(tmp_path / "doc-002.png")
    assert im.height == ScenePixelHeight
    assert im.width == ScenePixelHeight
    im = Image.open(tmp_path / "doc-003.png")
    assert im.height > ScenePixelHeight
    im = Image.open(tmp_path / "doc-004.png")
    assert im.height < ScenePixelHeight


def test_pdf_process_img_ridiculous_ratios(tmpdir):
    tmp_path = Path(tmpdir)
    f = tmp_path / "doc.pdf"
    d = fitz.open()
    d.new_page(width=1, height=200)
    d.save(f)
    with raises(ValueError, match="thin"):
        processFileToBitmaps(f, tmp_path)
    d = fitz.open()
    d.new_page(width=100, height=2)
    d.save(f)
    with raises(ValueError, match="wide"):
        processFileToBitmaps(f, tmp_path)


def test_pdf_process_error_no_file(tmpdir):
    tmp_path = Path(tmpdir)
    with raises(RuntimeError):
        processFileToBitmaps(tmp_path / "no_such_file.pdf", tmp_path)


def test_pdf_process_error_not_pdf(tmpdir):
    tmp_path = Path(tmpdir)
    textfile = tmp_path / "not_a_pdf.txt"
    with open(textfile, "w") as f:
        f.write("I'm a text file")
    with raises((TypeError, RuntimeError)):
        processFileToBitmaps(textfile, tmp_path)

    textfile = tmp_path / "not_a_pdf.pdf"
    with open(textfile, "w") as f:
        f.write("I'm a text file")
    with raises((TypeError, RuntimeError)):
        processFileToBitmaps(textfile, tmp_path)


def test_pdf_process_error_zip_is_not_pdf(tmpdir):
    tmp_path = Path(tmpdir)
    with working_directory(tmp_path):
        zipfile = shutil.make_archive("not_a_pdf", "zip", tmp_path, tmp_path)
    with raises(TypeError):
        processFileToBitmaps(zipfile, tmp_path)
