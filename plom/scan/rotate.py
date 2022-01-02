# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald

from pathlib import Path
import PIL.Image
import PIL.ExifTags
import subprocess
from warnings import warn

import exif

try:
    import jpegtran

    have_jpegtran = True
except ImportError:
    # warn("jpegtran-cffi package not available: jpeg rotations will be lossy")
    have_jpegtran = False


def rotateBitmap(fname, angle):
    """Rotate bitmap, possible in metadata.

    args:
        filename (pathlib.Path/str): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    If its a jpeg, wehave special handling, otherwise, we currently shell-out
    to the `mogrify` command line tool from ImageMagick.
    """
    assert angle in (0, 90, 180, 270, -90), f"Invalid rotation angle {angle}"
    fname = Path(fname)
    if fname.suffix.lower() in (".jpg", ".jpeg"):
        return rotate_bitmap_jpeg_exif(fname, angle)

    if angle == 0:
        return
    subprocess.run(
        ["mogrify", "-quiet", "-rotate", str(angle), fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


def rotate_bitmap_jpeg_exif(fname, angle):
    """Rotate jpeg using exif metadata rotations.

    args:
        filename (pathlib.Path): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    If the image already had a exif rotation tag it is ignored: the
    rotation is absolute, NOT relative to that existing transform.
    This is b/c the QR code reading bits earlier in the pipeline do not
    support exif tags: perhaps they should and we revisit this decision.
    """
    assert angle in (0, 90, 180, 270, -90), f"Invalid rotation angle {angle}"
    print(f"Rotation of {angle} on JPEG {fname}: doing metadata EXIF rotations")
    with open(fname, "rb") as f:
        im = exif.Image(f)
    if im.has_exif:
        print(f'{fname} has exif already, orientation: {im.get("orientation")}')
    # Notation is OrigTop_OrigLeft -> RIGHT_TOP (90 degree rot)
    table = {
        0: exif.Orientation.TOP_LEFT,
        90: exif.Orientation.RIGHT_TOP,
        180: exif.Orientation.BOTTOM_RIGHT,
        270: exif.Orientation.LEFT_BOTTOM,
        -90: exif.Orientation.LEFT_BOTTOM,
    }
    im.set("orientation", table[angle])
    with open(fname, "wb") as f:
        f.write(im.get_file())


def rotate_bitmap_jpeg_jpegtran_cffi(fname, angle):
    """Rotate jpeg (almost) losslessly using jpegtran-cffi if available.  DEPRECATED.

    args:
        filename (pathlib.Path): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    If available, this routine uses the `jpegtran-cffi` library for
    lossless jpeg rotations.  If that library is not available, there
    will be a loss of quality when rotating a jpeg image.
    """
    assert angle in (0, 90, 180, 270, -90), f"Invalid rotation angle {angle}"
    if angle == 0:
        return
    if have_jpegtran:
        print("**** Doing JPEG rotation {} on {}".format(angle, fname))
        im = jpegtran.JPEGImage(fname)
        im.rotate(angle).save(str(fname))
        return
    warn(
        f"Doing LOSSY jpeg rotation {angle} on {fname} [b/c jpegtran-cffi not installed]"
    )
    subprocess.run(
        ["mogrify", "-quiet", "-rotate", str(angle), fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )


def normalizeJPEGOrientation(f):
    """Transform image according to its Exif metadata.

    args:
        f (pathlib.Path/str): a jpeg file.

    Gives a warning if size not a multiple 16 b/c underlying library
    just quietly mucks up the bottom/right edge:
    https://github.com/jbaiter/jpegtran-cffi/issues/23
    """
    # First use Pillow: return early if we can, in case we don't have jpegtran
    pil_img = PIL.Image.open(f)
    exif = pil_img.getexif()
    all_tags = PIL.ExifTags.TAGS
    orientations = [v for k, v in exif.items() if all_tags.get(k) == "Orientation"]
    if not orientations or orientations[0] == 0:
        return
    if orientations[0] == 1:
        return

    if not have_jpegtran:
        warn(
            f"  jpeg {f} has EXIF orientation but no jpegtran-cffi: skipping orientation normalize"
        )
        return

    im = jpegtran.JPEGImage(f)
    if not im.exif_orientation:
        return

    if im.width % 16 or im.height % 16:
        warn(f'  jpeg "{f}" dims not mult of 16: re-orientations may be lossy')
    im2 = im.exif_autotransform()
    print(
        '  normalizing "{}" {}x{} to "{}" {}x{}'.format(
            im.exif_orientation,
            im.width,
            im.height,
            im2.exif_orientation,
            im2.width,
            im2.height,
        )
    )
    # str to workaround https://github.com/jbaiter/jpegtran-cffi/issues/28
    im2.save(str(f))
