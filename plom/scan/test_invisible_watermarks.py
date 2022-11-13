# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
from pytest import raises

from PIL import Image, ImageDraw

from plom import __version__
from plom.scan.scansToImages import (
    post_proc_metadata_into_jpeg,
    post_proc_metadata_into_png,
)


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
