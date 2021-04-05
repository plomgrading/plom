# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

import tempfile
import subprocess
import sys

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


f = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name


def test_frag_latex():
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    assert processFragment(frag, f)


def test_frag_broken_tex():
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    assert not processFragment(frag, f)


def test_frag_image_size():
    with resources.open_binary(plom.server, "target_Q_latex_plom.png") as fh:
        imgt = Image.open(fh)
        imgt.load()
    frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
    assert processFragment(frag, f)
    img = Image.open(f)
    # no more than 5% error in width/height
    assert relativeErr(img.width, imgt.width) < 0.05
    assert relativeErr(img.height, imgt.height) < 0.05

    frag = r"$z = \frac{x + 3}{y}$ and lots and lots more, so its much longer."
    assert processFragment(frag, f)
    img = Image.open(f)
    assert img.width > 2 * imgt.width


def test_frag_image():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        with open(target.name, "wb") as fh:
            fh.write(resources.read_binary(plom.server, "target_Q_latex_plom.png"))

        frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
        assert processFragment(frag, f)
        r = subprocess.run(
            ["compare", "-metric", "AE", f, target.name, "null"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # Note "AE" not "rmse" with transparency www.imagemagick.org/Usage/compare/
        s = r.stderr.decode()
        assert float(s) < 3000
