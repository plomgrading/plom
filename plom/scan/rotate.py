# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2024 Colin B. Macdonald

from __future__ import annotations

import logging
from pathlib import Path

import exif
from PIL import Image


log = logging.getLogger("scan")


def rotate_bitmap(fname: Path | str, angle: int, *, clockwise=False):
    """Rotate bitmap counterclockwise, possibly in metadata.

    Args:
        fname: file to rotate.
        angle: CCW angle of rotation: 0, 90, 180, 270, or -90.

    Keyword Args:
        clockwise (bool): By default this is False and we do anti-clockwise
            ("counter-clockwise") rotations.  Pass True if you want `+90`
            to be a clockwise rotation instead.

    Returns:
        None: modifies the image as a side effect.

    If its a jpeg, we have special handling, otherwise, we use the Python
    library ``PIL`` to open, rotate and then resave the image, replacing
    the original.
    """
    assert angle in (0, 90, 180, 270, -90), f"Invalid rotation angle {angle}"
    fname = Path(fname)
    if clockwise:
        if angle == 90:
            angle = -90
        elif angle == -90 or angle == 270:
            angle = 90

    if fname.suffix.lower() in (".jpg", ".jpeg"):
        return rotate_bitmap_jpeg_exif(fname, angle)

    if angle == 0:
        return
    # Note PIL does CCW (Issue #2585)
    img = Image.open(fname)
    new_img = img.rotate(angle, expand=True)
    new_img.save(fname)


def rotate_bitmap_jpeg_exif(fname: Path, angle: int):
    """Rotate jpeg using exif metadata rotations.

    Rotations are done cumulatively with any existing exif rotations.

    Args:
        fname: what file to rotate.
        angle: CCW angle of rotation 0, 90, 180, 270, or -90.

    Raises:
        ValueError: unexpected exif rotation that we cannot handle such
            as a mirror image.
    """
    assert angle in (0, 90, 180, 270, -90), f"Invalid rotation angle {angle}"
    log.info(f"Rotation of {angle:3} on JPEG {fname}: doing metadata EXIF rotations")
    with open(fname, "rb") as f:
        im = exif.Image(f)
    if im.has_exif:
        log.info(f'{fname} has exif already w/ orientation: {im.get("orientation")}')
        # Note: will raise ValueError on certain exif orientation
        existing_angle = _rot_angle_from_jpeg_exif_tag(im)
        if existing_angle:
            log.info(
                f"{fname}: adding {angle} to existing non-zero exif orientation {existing_angle}"
            )
        angle += existing_angle
        while True:
            if -90 <= angle < 360:
                break
            if angle >= 360:
                angle -= 360
            if angle < -90:
                angle += 360
    # Notation is OrigTop_OrigLeft -> RIGHT_TOP (-90 degree rot CCW)
    table = {
        0: exif.Orientation.TOP_LEFT,
        90: exif.Orientation.LEFT_BOTTOM,
        180: exif.Orientation.BOTTOM_RIGHT,
        -90: exif.Orientation.RIGHT_TOP,
        270: exif.Orientation.RIGHT_TOP,
    }
    im.set("orientation", table[angle])
    with open(fname, "wb") as f:
        f.write(im.get_file())


def pil_load_with_jpeg_exif_rot_applied(f):
    """Pillow's Image load does not apply exif orientation, so provide a helper that does.

    Args:
        f (str/pathlib.Path): a path to a file.

    If the input is not a jpeg, we simplify open it with ``PIL`` and
    return with no special processing.  If its a jpeg, we apply the exif
    rotations, then return.

    Returns:
        PIL.Image: with exif orientation applied.
    """
    f = Path(f)
    im = Image.open(f)
    if f.suffix.casefold() in (".jpg", ".jpeg"):
        r = rot_angle_from_jpeg_exif_tag(f)
        im = im.rotate(r, expand=True)
    return im


def rot_angle_from_jpeg_exif_tag(img_name):
    """If we have a jpeg and it has exif orientation data, return the angle of that rotation.

    That is, if you apply a rotation of this angle, the image will appear the same as
    the original would in an exif-aware viewer.  The angle is CCW.

    If not a jpeg, then return 0.
    """
    img_name = Path(img_name)
    if img_name.suffix not in (".jpg", ".jpeg"):
        return 0
    with open(img_name, "rb") as f:
        im = exif.Image(f)
    return _rot_angle_from_jpeg_exif_tag(im)


def _rot_angle_from_jpeg_exif_tag(im):
    # private help for the above
    #
    # im: the result of exif.Image(...)
    if not im.has_exif:
        return 0
    o = im.get("orientation")
    if o is None:
        return 0
    # print(f"{img_name} has exif orientation: {o}")
    if o == exif.Orientation.TOP_LEFT:
        return 0
    elif o == exif.Orientation.RIGHT_TOP:
        return -90
    elif o == exif.Orientation.BOTTOM_RIGHT:
        return 180
    elif o == exif.Orientation.LEFT_BOTTOM:
        return 90
    else:
        raise NotImplementedError(f"Unexpected exif orientation: {o}")
