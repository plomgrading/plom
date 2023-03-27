# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

from math import sqrt
from pathlib import Path
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

from PIL import Image
from PIL import ImageChops

import plom.scan
from plom.scan import rotate_bitmap
from plom.scan.rotate import pil_load_with_jpeg_exif_rot_applied
from plom.scan.rotate import rot_angle_from_jpeg_exif_tag


def relative_error(x, y):
    return abs(x - y) / abs(x)


def relative_error_vec(x, y):
    assert len(x) == len(y)
    err2norm = sqrt(sum([(x[i] - y[i]) ** 2 for i in range(len(x))]))
    x2norm = sqrt(sum([x[i] ** 2 for i in range(len(x))]))
    return err2norm / x2norm


cw_red_pixel_data = [
    (0, (32, 0)),
    (90, (63, 32)),
    (-90, (0, 32)),
    (270, (0, 32)),
    (180, (32, 63)),
]


ccw_red_pixel_data = [
    (0, (32, 0)),
    (90, (0, 32)),
    (-90, (63, 32)),
    (270, (63, 32)),
    (180, (32, 63)),
]


def test_rotate_png_cw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")
    b = (resources.files(plom.scan) / "test_rgb.png").read_bytes()
    # angle, and place where we expect a red pixel
    for angle, redpixel in cw_red_pixel_data:
        # make a copy
        f = tmpdir / f"img{angle}.png"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=True)
        # now load it back and check for a red pixel in the right place
        im = Image.open(f)
        palette = im.getpalette()
        if not palette:
            assert im.getpixel(redpixel) == (255, 0, 0)
            continue
        # if there was a palette, have to look up the colour by index
        idx = im.getpixel(redpixel)
        colour = palette[(3 * idx) : (3 * idx) + 3]
        assert colour == [255, 0, 0]


def test_rotate_png_ccw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")
    b = (resources.files(plom.scan) / "test_rgb.png").read_bytes()
    # angle, and place where we expect a red pixel
    for angle, redpixel in ccw_red_pixel_data:
        # make a copy
        f = tmpdir / f"img{angle}.png"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=False)
        # now load it back and check for a red pixel in the right place
        im = Image.open(f)
        palette = im.getpalette()
        if not palette:
            assert im.getpixel(redpixel) == (255, 0, 0)
            continue
        # if there was a palette, have to look up the colour by index
        idx = im.getpixel(redpixel)
        colour = palette[(3 * idx) : (3 * idx) + 3]
        assert colour == [255, 0, 0]


def test_rotate_jpeg_cw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make a lowish-quality jpeg and extract to bytes
    f = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(f, "JPEG", quality=2, optimize=True)
    with open(f, "rb") as fh:
        b = fh.read()

    # angle, and place where we expect a red pixel
    for angle, redpixel in cw_red_pixel_data:
        # make a copy
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=True)

        # now load it back and check for a red pixel in the right place
        im = pil_load_with_jpeg_exif_rot_applied(f)
        colour = im.getpixel(redpixel)
        assert relative_error_vec(colour, (255, 0, 0)) <= 0.1


def test_rotate_jpeg_ccw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make a lowish-quality jpeg and extract to bytes
    f = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(f, "JPEG", quality=2, optimize=True)
    with open(f, "rb") as fh:
        b = fh.read()

    # angle, and place where we expect a red pixel
    for angle, redpixel in ccw_red_pixel_data:
        # make a copy
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=False)

        # now load it back and check for a red pixel in the right place
        im = pil_load_with_jpeg_exif_rot_applied(f)
        colour = im.getpixel(redpixel)
        assert relative_error_vec(colour, (255, 0, 0)) <= 0.1


def test_rotate_jpeg_lossless_cw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make a lowish-quality jpeg and extract to bytes
    orig = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(orig, "JPEG", quality=2, optimize=True)
    with open(orig, "rb") as fh:
        b = fh.read()

    for angle in (0, 90, 180, 270, -90):
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=True)

        # r = rot_angle_from_jpeg_exif_tag(f)
        # print(("r=", r, "angle=", angle))
        # assert angle == r
        # TODO: Issue #2584?
        # TODO: 270 same as -90, some modular arith check instead
        # assert abs(r) == abs(angle)

        # q = QRextract(im2)
        # print(q)
        # print(q["NW"])

        # now load it back, rotate it back it it would make the original
        im = pil_load_with_jpeg_exif_rot_applied(f)
        im2 = Image.open(orig)
        # minus sign b/c PIL does CCW
        im2 = im2.rotate(-angle, expand=True)
        diff = ImageChops.difference(im, im2)
        diff.save(f"diff{angle}.png")
        assert not diff.getbbox()


def test_rotate_jpeg_lossless_ccw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make a lowish-quality jpeg and extract to bytes
    orig = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(orig, "JPEG", quality=2, optimize=True)
    with open(orig, "rb") as fh:
        b = fh.read()

    for angle in (0, 90, 180, 270, -90):
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(b)
        rotate_bitmap(f, angle, clockwise=False)

        # now load it back, rotate it back it it would make the original
        im = pil_load_with_jpeg_exif_rot_applied(f)
        im2 = Image.open(orig)
        im2 = im2.rotate(angle, expand=True)
        diff = ImageChops.difference(im, im2)
        diff.save(f"diff{angle}.png")
        assert not diff.getbbox()


def test_rotate_exif_read_back(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make jpeg and extract to bytes
    orig = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(orig, "JPEG", quality=90, optimize=True)
    with open(orig, "rb") as fh:
        jpg_bytes = fh.read()
    # png_bytes = (resources.files(plom.scan) / "test_rgb.png").read_bytes()

    for angle in (0, 90, 180, 270, -90):
        f = tmpdir / f"img{angle}.jpg"
        with open(f, "wb") as fh:
            fh.write(jpg_bytes)
        rotate_bitmap(f, angle, clockwise=False)

        r = rot_angle_from_jpeg_exif_tag(f)
        assert angle % 360 == r % 360

        # doesn't really work, maybe b/c PIL keeps making png into 2-channel?
        # f2 = tmpdir / f"img{angle}.png"
        # with open(f2, "wb") as fh:
        #     fh.write(png_bytes)
        # rotate_bitmap(f2, angle, clockwise=False)
        # im1 = pil_load_with_jpeg_exif_rot_applied(f)
        # im2 = Image.open(f2)
        # im2.convert("RGB")
        # diff = ImageChops.difference(im1, im2)
        # diff.save(f"diff{angle}.png")


def test_rotate_default_ccw(tmpdir):
    tmpdir = Path(tmpdir)
    # tmpdir = Path(".")

    # make jpeg and extract to bytes
    orig = tmpdir / "rgb.jpg"
    im = Image.open(resources.files(plom.scan) / "test_rgb.png")
    im.save(orig, "JPEG", quality=90, optimize=True)
    with open(orig, "rb") as fh:
        jpg_bytes = fh.read()

    for angle in (0, 90, 180, 270, -90):
        f1 = tmpdir / f"img{angle}_ccw.jpg"
        with open(f1, "wb") as fh:
            fh.write(jpg_bytes)
        rotate_bitmap(f1, angle, clockwise=False)

        f2 = tmpdir / f"img{angle}_default.jpg"
        with open(f2, "wb") as fh:
            fh.write(jpg_bytes)
        rotate_bitmap(f2, angle)

        im1 = pil_load_with_jpeg_exif_rot_applied(f1)
        im2 = pil_load_with_jpeg_exif_rot_applied(f2)
        diff = ImageChops.difference(im1, im2)
        diff.save(f"diff{angle}.png")
        assert not diff.getbbox()
