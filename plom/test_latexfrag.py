# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald

from io import BytesIO
import subprocess
import sys
import tempfile

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PIL import Image

import plom.server
from .textools import texFragmentToPNG as processFragment

# TODO: this too: pageNotSubmitted


def relativeErr(x, y):
    return float(abs(x - y)) / float(abs(x))


def test_frag_latex():
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    r, imgdata = processFragment(frag)
    assert r
    assert isinstance(imgdata, bytes)


def test_frag_broken_tex():
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    r, err = processFragment(frag)
    assert not r
    assert not isinstance(err, bytes)
    # TODO: still influx, probably a string or a dict but anyway not image


def test_frag_image_size():
    imgt = Image.open(resources.files(plom.server) / "target_Q_latex_plom.png")
    imgt.load()
    frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
    r, imgdata = processFragment(frag)
    assert r
    img = Image.open(BytesIO(imgdata))
    # no more than 10% error in width/height
    assert relativeErr(img.width, imgt.width) < 0.1
    assert relativeErr(img.height, imgt.height) < 0.1

    frag = r"$\mathbb{Q}$ \LaTeX\ Plom\\made\\taller\\not\\wider"
    r, imgdata = processFragment(frag)
    assert r
    img = Image.open(BytesIO(imgdata))
    # same width
    assert relativeErr(img.width, imgt.width) < 0.1
    # but much much taller
    assert img.height > 3 * imgt.height

    frag = r"$z = \frac{x + 3}{y}$ and lots and lots more, so its much longer."
    r, imgdata = processFragment(frag)
    assert r
    img = Image.open(BytesIO(imgdata))
    assert img.width > 2 * imgt.width


def test_frag_image():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        with open(target.name, "wb") as fh:
            fh.write(
                (resources.files(plom.server) / "target_Q_latex_plom.png").read_bytes()
            )

        valid, imgdata = processFragment(r"$\mathbb{Q}$ \LaTeX\ Plom")
        assert valid
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as img:
            with open(img.name, "wb") as f:
                f.write(imgdata)
            r = subprocess.run(
                ["compare", "-metric", "AE", img.name, target.name, "null"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            # Note "AE" not "rmse" with transparency www.imagemagick.org/Usage/compare/
            s = r.stderr.decode()
            assert float(s) < 3000
