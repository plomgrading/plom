# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2024 Colin B. Macdonald

import shutil

from pytest import raises
import fitz
from PIL import Image

from plom.misc_utils import working_directory
from plom import ScenePixelHeight
from plom.scan import processFileToBitmaps


def test_pdf_process_file_names(tmp_path) -> None:
    f = tmp_path / "mydoc-A-B.pdf"
    with fitz.open() as d:
        d.new_page()
        d.new_page()
        d.new_page()
        d.save(f)
    files = processFileToBitmaps(f, tmp_path)
    assert files[0].name == "mydoc-A-B-00001.png"
    assert files[1].name == "mydoc-A-B-00002.png"
    assert files[2].name == "mydoc-A-B-00003.png"


def test_pdf_process_also_side_effect_in_dir(tmp_path) -> None:
    f = tmp_path / "mydoc.pdf"
    where = tmp_path / "bar"
    where.mkdir()
    with fitz.open() as d:
        d.new_page()
        d.new_page()
        d.new_page()
        d.save(f)
    files = processFileToBitmaps(f, where)
    # no more and no less if we glob instead of using return value
    assert set(files) == set(where.glob("*"))


def test_pdf_process_img_height(tmp_path) -> None:
    f = tmp_path / "doc.pdf"
    with fitz.open() as d:
        d.new_page()
        d.save(f)
    (onefile,) = processFileToBitmaps(f, tmp_path)
    im = Image.open(onefile)
    assert im.height == ScenePixelHeight


def test_pdf_process_img_heights_other(tmp_path) -> None:
    f = tmp_path / "doc.pdf"
    with fitz.open() as d:
        d.new_page(width=500, height=842)
        d.new_page(width=100, height=100)
        d.new_page(width=100, height=842)
        d.new_page(width=400, height=100)
        d.save(f)
    files = processFileToBitmaps(f, tmp_path)
    im = Image.open(files[0])
    assert im.height == ScenePixelHeight
    im = Image.open(files[1])
    assert im.height == ScenePixelHeight
    assert im.width == ScenePixelHeight
    im = Image.open(files[2])
    assert im.height > ScenePixelHeight
    im = Image.open(files[3])
    assert im.height < ScenePixelHeight


def test_pdf_process_img_ridiculous_ratios(tmp_path) -> None:
    f = tmp_path / "doc.pdf"
    with fitz.open() as d:
        d.new_page(width=1, height=200)
        d.save(f)
    with raises(ValueError, match="thin"):
        processFileToBitmaps(f, tmp_path)
    with fitz.open() as d:
        d.new_page(width=100, height=2)
        d.save(f)
    with raises(ValueError, match="wide"):
        processFileToBitmaps(f, tmp_path)


def test_pdf_process_error_no_file(tmp_path) -> None:
    with raises(RuntimeError):
        processFileToBitmaps(tmp_path / "no_such_file.pdf", tmp_path)


def test_pdf_process_error_not_pdf(tmp_path) -> None:
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


def test_pdf_process_error_zip_is_not_pdf(tmp_path) -> None:
    with working_directory(tmp_path):
        zipfile = shutil.make_archive("not_a_pdf", "zip", tmp_path, tmp_path)
    with raises(TypeError):
        processFileToBitmaps(zipfile, tmp_path)
