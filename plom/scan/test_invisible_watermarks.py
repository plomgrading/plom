# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
import pytest

import exif
import fitz
from PIL import Image, ImageDraw

from plom import __version__
from plom.scan.scansToImages import (
    add_metadata_jpeg_comment,
    add_metadata_jpeg_exif,
    add_metadata_png,
    processFileToBitmaps,
)


white = (255, 255, 255)


def make_small_jpeg(dur):
    f = Path(dur) / "small_jpg_file.jpg"
    img = Image.new("RGB", (120, 100), color=(73, 109, 130))
    d = ImageDraw.Draw(img)
    d.text((2, 10), "small jpeg", fill=(255, 255, 0))
    img.save(f)
    return f


def make_a_png(dur, name="foo.png"):
    f = Path(dur) / name
    img = Image.new("RGB", (300, 200), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Here is some text in a png", fill=(255, 255, 0))
    img.save(f)
    return f


def make_jpeg(dur):
    """page-size jpeg image."""
    f = Path(dur) / "jpg_file.jpg"
    img = Image.new("RGB", (900, 1500), color=(73, 109, 130))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    img.save(f)
    return (f, img)


def make_png(dur):
    """page-size png image."""
    f = Path(dur) / "png_file.png"
    img = Image.new("RGB", (900, 1500), color=(108, 72, 130))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "some text", fill=(255, 255, 0))
    img.save(f)
    return (f, img)


def test_jpeg_comment_write(tmpdir):
    f = make_small_jpeg(tmpdir)
    add_metadata_jpeg_comment(f, "helloworld", 424242)
    with open(f, "rb") as fh:
        b = fh.read()
    b = str(b)
    assert "helloworld" in b
    assert "424242" in b
    assert "PlomVersion" in b


@pytest.mark.xfail
def test_jpeg_metadata_with_existing_exif(tmpdir):
    # TODO: also try pre-modifying exif via PIL
    tmp_path = Path(tmpdir)
    jpg_file, _ = make_jpeg(tmp_path)
    im_shell = exif.Image(jpg_file)
    im_shell.set("user_comment", "I will be overwritten")
    with open(jpg_file, "wb") as f:
        f.write(im_shell.get_file())
    add_metadata_jpeg_exif(jpg_file, "helloworld", 424242)


def test_png_metadata(tmpdir):
    pngfile = make_a_png(tmpdir)
    img = Image.open(pngfile)
    assert not img.text
    del img
    add_metadata_png(pngfile, "helloworld", 424242)
    img = Image.open(pngfile)
    assert img.text["PlomVersion"] == __version__
    assert img.text["SourceBundle"] == "helloworld"
    assert int(img.text["SourceBundlePosition"]) == 424242


def test_pdf_can_extract_png_and_jpeg(tmpdir):
    tmp_path = Path(tmpdir)

    jpg_file, jpg_img = make_jpeg(tmpdir)
    png_file, png_img = make_png(tmpdir)

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

    small_jpg_file = make_small_jpeg(tmp_path)
    jpg_file, jpg_img = make_jpeg(tmp_path)

    f = tmp_path / "doc.pdf"
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
    (_,) = tmp_path.glob("doc-001.*")
    im = Image.open(_)
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c text on page
    (_,) = tmp_path.glob("doc-002.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c two images
    (_,) = tmp_path.glob("doc-003.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white


def test_pdf_identical_pages_render_png_made_unique(tmpdir):
    tmp_path = Path(tmpdir)

    pdf_file = tmp_path / "doc.pdf"
    d = fitz.open()
    rect = fitz.Rect(20, 20, 480, 820)
    p = d.new_page(width=500, height=842)
    p.insert_textbox(rect, "deja vu")
    d.copy_page(0)
    d.ez_save(pdf_file)

    processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)

    im = Image.open(tmp_path / "doc-001.png")
    im2 = Image.open(tmp_path / "doc-002.png")
    assert "RandomUUID" in im.text.keys()
    assert im.text["RandomUUID"] != im2.text["RandomUUID"]

    processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)
    f1 = tmp_path / "doc-001.png"
    f2 = tmp_path / "doc-002.png"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 == b2


def test_pdf_identical_pages_render_jpeg_made_unique(tmpdir):
    tmp_path = Path(tmpdir)

    # need some noise so we get jpeg
    png_file = tmp_path / "img.png"
    img = Image.radial_gradient("L")
    img.save(png_file)
    png_file2 = tmp_path / "img2.png"
    img = Image.effect_mandelbrot((1000, 1200), (-2, -1.3, 0.5, 1.3), 90)
    img.save(png_file2)

    pdf_file = tmp_path / "doc.pdf"
    d = fitz.open()
    rect = fitz.Rect(20, 20, 480, 820)
    rect2 = fitz.Rect(10, 10, 200, 200)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=png_file2)
    p.insert_image(rect2, filename=png_file)
    d.copy_page(0)
    d.ez_save(pdf_file)
    processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)
    f1 = tmp_path / "doc-001.jpg"
    f2 = tmp_path / "doc-002.jpg"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 != b2

    processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)
    f1 = tmp_path / "doc-001.jpg"
    f2 = tmp_path / "doc-002.jpg"
    with open(f1, "rb") as f:
        b1 = f.read()
    with open(f2, "rb") as f:
        b2 = f.read()
    assert b1 == b2


def test_pdf_can_extract_png_and_jpeg_uniquified(tmpdir):
    tmp_path = Path(tmpdir)

    jpg_file, jpg_img = make_jpeg(tmp_path)
    png_file, png_img = make_png(tmp_path)

    pdf_file = tmp_path / "doc.pdf"
    d = fitz.open()
    rect = fitz.Rect(20, 20, 480, 820)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=jpg_file)
    d.copy_page(0)
    p = d.new_page(width=500, height=842)
    p.insert_image(rect, filename=png_file)
    d.copy_page(2)
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
