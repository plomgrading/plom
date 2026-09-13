# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2026 Jax Lim

from statistics import mean
from typing import Any

import zxingcpp
from PIL import Image

from .rotate import pil_load_with_jpeg_exif_rot_applied


def _findCorner(mx: float, my: float, dim: tuple[int, int]):
    """Determines the x-y coordinates and relative location of the given QR code's approximate centre.

    Args:
        mx: floating point x coord, centre of the QR code.
        my: floating point y coord, centre of the QR code.
        dim: pair of ints that correspond to the dimensions of
            the image that contains the QR code.

    Returns:
        A 2-char string, one of "NE", "NW", "SW", "SE", depending on the
        relative location of the QR code, or "??" if the QR code cannot
        be assigned a corner,
    """
    width, height = dim

    NS = "?"
    EW = "?"
    if my < 0.4 * height:
        NS = "N"
    elif my > 0.6 * height:
        NS = "S"
    else:
        return "??"
    if mx < 0.4 * width:
        EW = "W"
    elif mx > 0.6 * width:
        EW = "E"
    else:
        return "??"
    return NS + EW


def QRextract(image, *, rotation: int = 0) -> dict[str, dict[str, Any]]:
    """Decode the QR codes in an image.

    Args:
        image (str/pathlib.Path/PIL.Image): an image filename, either in
            the local dir or specified e.g., using `pathlib.Path`.  Can
            also be an instance of Pillow's `Image`.

    Keyword Args:
        rotation (int): Rotate the image by 90, -90, 180 or 270 degrees
            counterclockwise prior to reading the QR codes. Defaults to 0.

    Returns:
        A dict with keys "NW", "NE", "SW", "SE", each with a dict containing
        'raw_qr_stinrg', 'x', 'y' (the horizontal and vertical pixel coordinates
        of the QR code), 'orientation' (the rotation ccw of the QR code in degrees,
        currently an integer).
        The dict is empty if no QR codes found in that corner.
        TODO: if multiple QR codes are found in one corner...?!?
    """
    cornerQR: dict[str, Any] = {"NW": {}, "NE": {}, "SW": {}, "SE": {}, "others": []}

    if not isinstance(image, Image.Image):
        image = pil_load_with_jpeg_exif_rot_applied(image)

    if rotation != 0:
        assert rotation in (-90, 90, 270, 180)
        image = image.rotate(rotation, expand=True)

    # PIL does lazy loading.  Force loading now so we see errors now.
    # Otherwise, zxing-cpp might hide error messages, Issue #2597
    image.load()

    qr_code_formats = zxingcpp.BarcodeFormat.QRCode | zxingcpp.BarcodeFormat.MicroQRCode
    qrlist = zxingcpp.read_barcodes(image, formats=qr_code_formats)
    for qr in qrlist:
        qr_polygon = [
            qr.position.top_left,
            qr.position.top_right,
            qr.position.bottom_left,
            qr.position.bottom_right,
        ]
        x_coord = mean([p.x for p in qr_polygon])
        y_coord = mean([p.y for p in qr_polygon])

        d = {
            "raw_qr_string": qr.text,
            "x": x_coord,
            "y": y_coord,
            "orientation": -qr.orientation,  # Zxing has + meaning cw (!)
        }
        cnr = _findCorner(x_coord, y_coord, image.size)
        if cnr in cornerQR.keys() and not cornerQR[cnr]:
            cornerQR[cnr].update(d)
        else:
            # if we find two QR codes in a corner, one of them will end up
            # here, currently just based on whatever one we look at first
            # TODO: which seems rather poorly posed.
            cornerQR["others"].append(d)

    return cornerQR
