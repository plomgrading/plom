# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from io import BytesIO

from PIL import Image

from django.db.models.fields.files import ImageFieldFile


class ExifNumbers:
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvv
    # sigh - exif rotation information. sigh.
    # see https://exiftool.org/TagNames/EXIF.html  or
    # https://www.daveperrett.com/articles/2012/07/28/exif-orientation-handling-is-a-ghetto/
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    # The tag to get orientation info from an exif-dict.
    # the exif orientation info is stored in the exif dict with key 274
    ORIENTATION = 274
    # store the orientation information as clock-values.
    # ie if we take a photo of a clock with its hands at twelve, then
    # an exif rotation with value '3' corresponds to the clock appearing with
    # its hands at 6-oclock. Hence we will label that exif-orientation-value 'six oclock'.
    TWELVE_OCLOCK = 1  # is sometimes called "top left"
    SIX_OCLOCK = 3  # is sometimes "bottom right" - repair by 180 rotation
    NINE_OCLOCK = 6  # is sometimes "left bottom" - repair by minus-90 ccw rot
    THREE_OCLOCK = 8  # is sometimes "right top" - repair by plus-90 ccw rot


def hard_rotate_image_from_file_by_exif_and_angle(
    image_file: ImageFieldFile,
    *,
    theta: int | None = None,
    save_format: str = "png",
) -> bytes:
    """Construct an image hard-rotated by the given angle and any exif.

    Args:
        image_file: the Django image "FieldFile" to be rotated.  Exactly
            what this is depends on the storage being used.  We can read
            from it.  We will not write to it.

    Keyword Args:
        theta: the anti-clockwise angle to rotate (not including any
            exif rotations) - default 0.
        save_format: the format in which to save - default is png.

    Returns:
        The bytes of a new image (the original is unchanged).
    """
    # We will rotate image by theta anti-clockwise.
    if theta is None:
        theta = 0
    with Image.open(image_file) as tmp_img:
        # rotate anti-clockwise by theta - get current orientation info from exif
        exif_orient = tmp_img.getexif().get(
            ExifNumbers.ORIENTATION, ExifNumbers.TWELVE_OCLOCK
        )
        if exif_orient == ExifNumbers.TWELVE_OCLOCK:
            pass
        elif exif_orient == ExifNumbers.SIX_OCLOCK:
            theta += 180
        elif exif_orient == ExifNumbers.NINE_OCLOCK:
            theta -= 90
        elif exif_orient == ExifNumbers.THREE_OCLOCK:
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
