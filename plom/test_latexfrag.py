# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2025 Colin B. Macdonald

import subprocess
import tempfile
from importlib import resources
from io import BytesIO
from pathlib import Path

from PIL import Image

import plom

from .textools import texFragmentToPNG as processFragment

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
    res = resources.files(plom) / "test_target_latex_white.png"
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


def abs_error_between_images(img1: Path, img2: Path) -> float:
    """The number of pixels that differ between two images: "AE" error from ImageMagick."""
    r = subprocess.run(
        ["compare", "-metric", "AE", img1.name, img2.name, "null:"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    # Note "AE" not "rmse" with transparency www.imagemagick.org/Usage/compare/
    s = r.stderr.decode()
    if "(" in s:
        # Fedora 42, Issue #3851, looks like `<float> (<AE>)`
        return float(s.split()[1].strip("()"))
    return float(s)


def test_frag_image() -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        # TODO: target is antialiased with white rather than transparent;
        # consider replacing it and tightening the tolerance below.
        with open(target.name, "wb") as fh:
            fh.write(
                (resources.files(plom) / "test_target_latex_white.png").read_bytes()
            )

        valid, imgdata = processFragment(r"$\mathbb{Q}$ \LaTeX\ Plom")
        assert valid
        assert isinstance(imgdata, bytes)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as img:
            with open(img.name, "wb") as f:
                f.write(imgdata)
            assert abs_error_between_images(img, target) < 3000
