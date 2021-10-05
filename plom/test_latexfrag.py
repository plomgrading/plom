# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

from io import BytesIO
import subprocess
import sys
import tempfile

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from pytest import raises

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
    with resources.open_binary(plom.server, "target_Q_latex_plom.png") as fh:
        imgt = Image.open(fh)
        imgt.load()
    frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
    r, imgdata = processFragment(frag)
    assert r
    img = Image.open(BytesIO(imgdata))
    # no more than 10% error in width/height
    assert relativeErr(img.width, imgt.width) < 0.1
    assert relativeErr(img.height, imgt.height) < 0.1

    frag = r"$z = \frac{x + 3}{y}$ and lots and lots more, so its much longer."
    r, imgdata = processFragment(frag)
    assert r
    img = Image.open(BytesIO(imgdata))
    assert img.width > 2 * imgt.width


def test_frag_image():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        with open(target.name, "wb") as fh:
            fh.write(resources.read_binary(plom.server, "target_Q_latex_plom.png"))

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
