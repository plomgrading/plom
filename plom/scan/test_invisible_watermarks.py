# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
from pytest import raises

import fitz
from PIL import Image, ImageDraw

from plom import __version__
from plom.scan.scansToImages import (
    post_proc_metadata_into_jpeg,
    post_proc_metadata_into_png,
)


white = (255, 255, 255)


def make_a_jpeg(dur, name="foo.jpg"):
    f = Path(dur) / name
    img = Image.new("RGB", (300, 200), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Here is some text in a jpeg", fill=(255, 255, 0))
    img.save(f)
    return f


def make_a_png(dur, name="foo.png"):
    f = Path(dur) / name
    img = Image.new("RGB", (300, 200), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Here is some text in a png", fill=(255, 255, 0))
    img.save(f)
    return f


def test_jpeg_comment_write(tmpdir):
    jpg = make_a_jpeg(tmpdir)
    post_proc_metadata_into_jpeg(jpg, "helloworld", 424242)
    with open(jpg, "rb") as f:
        b = f.read()
    b = str(b)
    assert "helloworld" in b
    assert "424242" in b
    assert "PlomVersion" in b


def test_png_metadata(tmpdir):
    pngfile = make_a_png(tmpdir)
    img = Image.open(pngfile)
    assert not img.text
    del img
    post_proc_metadata_into_png(pngfile, "helloworld", 424242)
    img = Image.open(pngfile)
    assert img.text["PlomVersion"] == __version__
    assert img.text["SourceBundle"] == "helloworld"
    assert int(img.text["SourceBundlePosition"]) == 424242


# TODO: make jpeg and put 3 of them as 3 pages

from plom.scan.scansToImages import processFileToBitmaps


def test_pdf_can_extract_png_and_jpeg(tmpdir):
    tmp_path = Path(tmpdir)

    jpg_file = tmp_path / "jpg_file.jpg"
    jpg_img = Image.new("RGB", (900, 1500), color=(73, 109, 137))
    d = ImageDraw.Draw(jpg_img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    jpg_img.save(jpg_file)

    png_file = tmp_path / "png_file.png"
    png_img = Image.new("RGB", (900, 1500), color=(73, 109, 137))
    d = ImageDraw.Draw(png_img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    png_img.save(png_file)

    f = tmp_path / "doc.pdf"
    d = fitz.open()
    p = d.new_page(width=500, height=842)
    rect = fitz.Rect(20, 20, 480, 820)
    p.insert_image(rect, filename=jpg_file)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=png_file)
    d.ez_save(f)
    processFileToBitmaps(f, tmp_path, do_not_extract=False)

    # was extracted: no white border and size matches input
    im = Image.open(tmp_path / "doc-001.jpeg")
    assert im.format == "JPEG"
    assert im.width == jpg_img.width
    assert im.getpixel((0, 0)) != white

    im = Image.open(tmp_path / "doc-002.png")
    assert im.format == "PNG"
    assert im.width == png_img.width
    assert im.getpixel((0, 0)) != white


def test_pdf_no_extract_cases(tmpdir):
    tmp_path = Path(tmpdir)

    small_jpg_file = tmp_path / "small_jpg_file.jpg"
    img = Image.new("RGB", (60, 100), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((2, 10), "small", fill=(255, 255, 0))
    img.save(small_jpg_file)

    jpg_file = tmp_path / "jpg_file.jpg"
    jpg_img = Image.new("RGB", (900, 1500), color=(73, 109, 137))
    d = ImageDraw.Draw(jpg_img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    jpg_img.save(jpg_file)

    f = tmp_path / "doc_no_extract.pdf"
    d = fitz.open()

    p = d.new_page(width=500, height=842)
    p.insert_image(fitz.Rect(20, 20, 480, 820), filename=small_jpg_file)

    p = d.new_page(width=500, height=842)
    p.insert_image(fitz.Rect(20, 50, 480, 820), filename=jpg_file)
    p.insert_textbox(fitz.Rect(10, 10, 480, 100), "hello world")

    p = d.new_page(width=500, height=842)
    p.insert_image(fitz.Rect(20, 50, 480, 820), filename=jpg_file)
    p.insert_image(fitz.Rect(10, 10, 100, 100), filename=small_jpg_file)

    d.save(f)
    processFileToBitmaps(f, tmp_path, do_not_extract=False)

    # do not extract small images
    (_,) = tmp_path.glob(f"{f.stem}-001.*")
    im = Image.open(_)
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c text on page
    (_,) = tmp_path.glob(f"{f.stem}-002.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c two images
    (_,) = tmp_path.glob(f"{f.stem}-003.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white


def test_pdf_can_extract_png_and_jpeg_uniquified(tmpdir):
    tmp_path = Path(tmpdir)

    jpg_file = tmp_path / "jpg_file.jpg"
    jpg_img = Image.new("RGB", (900, 1500), color=(73, 109, 137))
    d = ImageDraw.Draw(jpg_img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    jpg_img.save(jpg_file)

    png_file = tmp_path / "png_file.png"
    png_img = Image.new("RGB", (900, 1500), color=(73, 109, 137))
    d = ImageDraw.Draw(png_img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    png_img.save(png_file)

    pdf_file = tmp_path / "doc.pdf"
    d = fitz.open()
    rect = fitz.Rect(20, 20, 480, 820)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=jpg_file)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=jpg_file)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=png_file)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=png_file)
    d.ez_save(pdf_file)
    processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)

    f1 = tmp_path / "doc-001.jpeg"
    f2 = tmp_path / "doc-002.jpeg"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 != b2

    im = Image.open(tmp_path / "doc-003.png")
    im2 = Image.open(tmp_path / "doc-004.png")
    assert "RandomUUID" in im.text.keys()
    assert im.text["RandomUUID"] != im2.text["RandomUUID"]

    processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)
    f1 = tmp_path / "doc-001.jpeg"
    f2 = tmp_path / "doc-002.jpeg"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 == b2
    f1 = tmp_path / "doc-003.png"
    f2 = tmp_path / "doc-004.png"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 == b2
