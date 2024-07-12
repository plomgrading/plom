# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Colin B. Macdonald

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


def test_jpeg_comment_write(tmp_path) -> None:
    f = make_small_jpeg(tmp_path)
    add_metadata_jpeg_comment(f, "helloworld", 424242)
    with open(f, "rb") as fh:
        _b = fh.read()
    b = str(_b)
    assert "helloworld" in b
    assert "424242" in b
    assert "PlomVersion" in b


@pytest.mark.xfail
def test_jpeg_metadata_with_existing_exif(tmp_path) -> None:
    # TODO: also try pre-modifying exif via PIL
    jpg_file, _ = make_jpeg(tmp_path)
    im_shell = exif.Image(jpg_file)
    im_shell.set("user_comment", "I will be overwritten")
    with open(jpg_file, "wb") as f:
        f.write(im_shell.get_file())
    add_metadata_jpeg_exif(jpg_file, "helloworld", 424242)


def test_png_metadata(tmp_path) -> None:
    pngfile = make_a_png(tmp_path)
    img = Image.open(pngfile)
    assert not img.text  # type: ignore[attr-defined]
    del img
    add_metadata_png(pngfile, "helloworld", 424242)
    img = Image.open(pngfile)
    textdict = img.text  # type: ignore[attr-defined]
    assert textdict["PlomVersion"] == __version__
    assert textdict["SourceBundle"] == "helloworld"
    assert int(textdict["SourceBundlePosition"]) == 424242


def test_pdf_can_extract_png_and_jpeg(tmp_path) -> None:
    jpg_file, jpg_img = make_jpeg(tmp_path)
    png_file, png_img = make_png(tmp_path)

    f = tmp_path / "doc.pdf"
    with fitz.open() as d:
        p = d.new_page(width=500, height=842)
        rect = fitz.Rect(20, 20, 480, 820)
        p.insert_image(rect, filename=jpg_file)
        p = d.new_page(width=500, height=842)
        p.insert_image(rect, filename=png_file)
        d.ez_save(f)
    files = processFileToBitmaps(f, tmp_path, do_not_extract=False)

    # was extracted: no white border and size matches input
    assert files[0].suffix.casefold() in (".jpg", ".jpeg")
    im = Image.open(files[0])
    assert im.format == "JPEG"
    assert im.width == jpg_img.width
    assert im.getpixel((0, 0)) != white

    assert files[1].suffix.casefold() == ".png"
    im = Image.open(files[1])
    assert im.format == "PNG"
    assert im.width == png_img.width
    assert im.getpixel((0, 0)) != white


def test_pdf_no_extract_cases(tmp_path) -> None:
    small_jpg_file = make_small_jpeg(tmp_path)
    jpg_file, jpg_img = make_jpeg(tmp_path)

    f = tmp_path / "doc.pdf"
    with fitz.open() as d:
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
    (_,) = tmp_path.glob("doc-*01.*")
    im = Image.open(_)
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c text on page
    (_,) = tmp_path.glob("doc-*02.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white

    # big enough image but no extract b/c two images
    (_,) = tmp_path.glob("doc-*03.*")
    im = Image.open(_)
    assert im.width != jpg_img.width
    assert im.getpixel((0, 0)) == white


def test_pdf_identical_pages_render_png_made_unique(tmp_path) -> None:
    pdf_file = tmp_path / "doc.pdf"
    with fitz.open() as d:
        rect = fitz.Rect(20, 20, 480, 820)
        p = d.new_page(width=500, height=842)
        p.insert_textbox(rect, "deja vu")
        d.copy_page(0)
        d.ez_save(pdf_file)

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)

    im = Image.open(files[0])
    im2 = Image.open(files[1])
    assert "RandomUUID" in im.text.keys()  # type: ignore[attr-defined]
    assert im.text["RandomUUID"] != im2.text["RandomUUID"]  # type: ignore[attr-defined]

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)

    for f in files:
        assert f.suffix.casefold() == ".png"

    with open(files[0], "rb") as f:
        b1 = f.read()
    with open(files[1], "rb") as f:
        b2 = f.read()
    assert b1 == b2


def test_pdf_identical_pages_render_jpeg_made_unique(tmp_path) -> None:
    # need some noise so we get jpeg
    png_file = tmp_path / "img.png"
    img = Image.radial_gradient("L")
    img.save(png_file)
    png_file2 = tmp_path / "img2.png"
    img = Image.effect_mandelbrot((1000, 1200), (-2, -1.3, 0.5, 1.3), 90)
    img.save(png_file2)

    pdf_file = tmp_path / "doc.pdf"
    with fitz.open() as d:
        rect = fitz.Rect(20, 20, 480, 820)
        rect2 = fitz.Rect(10, 10, 200, 200)
        p = d.new_page(width=500, height=842)
        p.insert_image(rect, filename=png_file2)
        p.insert_image(rect2, filename=png_file)
        d.copy_page(0)
        d.ez_save(pdf_file)

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)

    for f in files:
        assert f.suffix.casefold() in (".jpg", ".jpeg")

    with open(files[0], "rb") as f:
        b1 = f.read()
    with open(files[1], "rb") as f:
        b2 = f.read()
    assert b1 != b2

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)

    for f in files:
        assert f.suffix.casefold() in (".jpg", ".jpeg")

    with open(files[0], "rb") as f:
        b1 = f.read()
    with open(files[1], "rb") as f:
        b2 = f.read()
    assert b1 == b2


def test_pdf_can_extract_png_and_jpeg_uniquified(tmp_path) -> None:
    jpg_file, jpg_img = make_jpeg(tmp_path)
    png_file, png_img = make_png(tmp_path)

    pdf_file = tmp_path / "doc.pdf"
    with fitz.open() as d:
        rect = fitz.Rect(20, 20, 480, 820)
        p = d.new_page(width=500, height=842)
        p.insert_image(rect, filename=jpg_file)
        d.copy_page(0)
        p = d.new_page(width=500, height=842)
        p.insert_image(rect, filename=png_file)
        d.copy_page(2)
        d.ez_save(pdf_file)

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=True)

    for f in files[:2]:
        assert f.suffix.casefold() in (".jpg", ".jpeg")
    with open(files[0], "rb") as f:
        b1 = f.read()
    with open(files[1], "rb") as f:
        b2 = f.read()
    assert b1 != b2

    for f in files[2:]:
        assert f.suffix.casefold() == ".png"
    im = Image.open(files[2])
    im2 = Image.open(files[3])
    assert "RandomUUID" in im.text.keys()  # type: ignore[attr-defined]
    assert im.text["RandomUUID"] != im2.text["RandomUUID"]  # type: ignore[attr-defined]

    files = processFileToBitmaps(pdf_file, tmp_path, add_metadata=False)

    with open(files[0], "rb") as f:
        b1 = f.read()
    with open(files[1], "rb") as f:
        b2 = f.read()
    assert b1 == b2

    with open(files[2], "rb") as f:
        b1 = f.read()
    with open(files[3], "rb") as f:
        b2 = f.read()
    assert b1 == b2
