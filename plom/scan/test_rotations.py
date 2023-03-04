# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

from math import sqrt
from pathlib import Path
import sys

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PIL import Image
from PIL import ImageChops

import plom.scan
from plom.scan import rotate_bitmap
from plom.finish.examReassembler import rot_angle_from_jpeg_exif_tag


def relative_error(x, y):
    return abs(x - y) / abs(x)


def relative_error_vec(x, y):
    assert len(x) == len(y)
    err2norm = sqrt(sum([(x[i] - y[i]) ** 2 for i in range(len(x))]))
    x2norm = sqrt(sum([x[i] ** 2 for i in range(len(x))]))
    return err2norm / x2norm


def test_rotate_png(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")
    b = (resources.files(plom.scan) / "rgb.png").read_bytes()
    # angle, and place where we expect a red pixel
    for angle, redpixel in [
        (0, (32, 0)),
        (90, (63, 32)),
        (-90, (0, 32)),
        (270, (0, 32)),
        (180, (32, 63)),
    ]:
        # make a copy
        f = tmpdir / f"img{angle}.png"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle)
        # now load it back and check for a red pixel in the right place
        im = Image.open(f)
        im.load()
        palette = im.getpalette()
        if not palette:
            assert im.getpixel(redpixel) == (255, 0, 0)
            continue
        # if there was a palette, have to look up the colour by index
        idx = im.getpixel(redpixel)
        colour = palette[(3 * idx) : (3 * idx) + 3]
        assert colour == [255, 0, 0]


def pil_load_with_jpeg_exif_rot_applied(f):
    im = Image.open(f)
    im.load()
    r = rot_angle_from_jpeg_exif_tag(f)
    im = im.rotate(r, expand=True)
    return im


def test_rotate_jpeg(tmpdir):
    tmpdir = Path(tmpdir)
    tmpdir = Path(".")
    # make a lowish-quality jpeg
    orig = tmpdir / "rgb.jpg"
    with (resources.files(plom.scan) / "rgb.png") as fh:
        im = Image.open(fh)
        im.load()
        im.save(orig, "JPEG", quality=2, optimize=True)
    with open(orig, "rb") as fh:
        b = fh.read()
    # angle, and place where we expect a red pixel
    for angle, redpixel in [
        (0, (32, 0)),
        (90, (63, 32)),
        (-90, (0, 32)),
        (270, (0, 32)),
        (180, (32, 63)),
    ]:
        # make a copy
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle)
        # now load it back and check for a red pixel in the right place
        im = pil_load_with_jpeg_exif_rot_applied(f)
        colour = im.getpixel(redpixel)
        assert relative_error_vec(colour, (255, 0, 0)) <= 0.1
