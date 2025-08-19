# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2025 Colin B. Macdonald

import tempfile
from importlib import resources
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

import plom
from plom.textools import texFragmentToPNG as processFragment

# TODO: this too: pageNotSubmitted


def relativeErr(x, y):
    return float(abs(x - y)) / float(abs(x))


def test_frag_latex() -> None:
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    r, imgdata = processFragment(frag)
    assert r
    assert isinstance(imgdata, bytes)


def test_frag_broken_tex() -> None:
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    r, err = processFragment(frag)
    assert not r
    assert not isinstance(err, bytes)
    # TODO: still influx, probably a string or a dict but anyway not image


def test_frag_image_size() -> None:
    res = resources.files(plom) / "test_target_latex.png"
    # mypy stumbling over resource Traversables?
    imgt = Image.open(res)  # type: ignore[arg-type]
    frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
    r, imgdata = processFragment(frag)
    assert r
    assert isinstance(imgdata, bytes)
    img = Image.open(BytesIO(imgdata))
    # no more than 10% error in width/height
    assert relativeErr(img.width, imgt.width) < 0.1
    assert relativeErr(img.height, imgt.height) < 0.1

    frag = r"$\mathbb{Q}$ \LaTeX\ Plom\\made\\taller\\not\\wider"
    r, imgdata = processFragment(frag)
    assert r
    assert isinstance(imgdata, bytes)
    img = Image.open(BytesIO(imgdata))
    # same width
    assert relativeErr(img.width, imgt.width) < 0.1
    # but much much taller
    assert img.height > 3 * imgt.height

    frag = r"$z = \frac{x + 3}{y}$ and lots and lots more, so its much longer."
    r, imgdata = processFragment(frag)
    assert r
    assert isinstance(imgdata, bytes)
    img = Image.open(BytesIO(imgdata))
    assert img.width > 2 * imgt.width


def percent_error_between_images(img1: Path, img2: Path) -> float:
    """A percentage difference of pixels that differ between two images.

    Returns:
        A percentage as a floating point number in [0, 100].  If the
        images are the same, return 0.  If the images are as different
        as can be (e.g., inverse of each other) then return 100.
    """
    with Image.open(img1) as im1, Image.open(img2) as im2:
        d = ImageChops.difference(im1, im2)
        total = 0.0
        for pixel in d.getdata():  # type: ignore[attr-defined]
            assert 0 <= pixel <= 255, "Incorrectly assumed pixel values in [0, 255]"
            total += float(pixel) / 255.0
            print((pixel, total))
        return 100 * total / (d.width * d.height)


def test_frag_image() -> None:
    valid, imgdata = processFragment(r"$\mathbb{Q}$ \LaTeX\ Plom")
    assert valid
    assert isinstance(imgdata, bytes)
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / "new_image.png"
        with img.open("wb") as f:
            f.write(imgdata)

        target_img = Path(td) / "target.png"
        with target_img.open("wb") as f:
            f.write((resources.files(plom) / "test_target_latex.png").read_bytes())

        assert percent_error_between_images(img, target_img) < 0.1

        # older image with poor quality white-tinged antialiasing
        target_old = Path(td) / "target_old.png"
        with target_old.open("wb") as f:
            f.write((resources.files(plom) / "test_target_latex_old.png").read_bytes())
        # somewhat close
        assert percent_error_between_images(img, target_old) < 10
        # but not too close
        assert percent_error_between_images(img, target_old) > 0.1
