# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from io import BytesIO
from PIL import Image
from typing import Optional

from django.db.models.fields.files import ImageFieldFile


def hard_rotate_image_from_file_by_exif_and_angle(
    image_file: ImageFieldFile,
    *,
    theta: Optional[int] = None,
    save_format: Optional[str] = "png",
) -> bytes:
    """Construct an image hard-rotated by the given angle and any exif.

    Args:
        image_file: the Django image field file to be rotated

    Keyword Args:
        theta: the angle to rotate (not inc any exif rotations) - default 0.
        save_format: the format in which to save - default is png.

    Returns:
        (bytes) bytes of the image
    """
    if theta is None:
        theta = 0
    with Image.open(image_file) as tmp_img:
        exif_orient = tmp_img.getexif().get(274, 1)
        if exif_orient == 1:
            pass
        elif exif_orient == 3:
            theta += 180
        elif exif_orient == 6:
            theta -= 90
        elif exif_orient == 8:
            theta += 90
        else:
            raise ValueError(
                f"Do not recognise this exif orientation value {exif_orient}"
            )
        fh = BytesIO()
        if theta == 0:
            # send back unrotated png
            tmp_img.save(fh, save_format)
        else:
            # rotate the image (expand if needed) and return as png.
            tmp_img.rotate(theta, expand=True).save(fh, save_format)

        return fh.getvalue()
