# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald

import logging
from pathlib import Path
import subprocess

import exif


log = logging.getLogger("scan")


def rotateBitmap(fname, angle):
    """Rotate bitmap, possibly in metadata.

    args:
        filename (pathlib.Path/str): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    If its a jpeg, we have special handling, otherwise, we currently shell-out
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
    log.info(f"Rotation of {angle:3} on JPEG {fname}: doing metadata EXIF rotations")
    with open(fname, "rb") as f:
        im = exif.Image(f)
    if im.has_exif:
        log.info(f'{fname} has exif already, orientation: {im.get("orientation")}')
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
