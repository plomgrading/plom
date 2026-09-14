# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024, 2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2026 Jax Lim

from statistics import mean
from typing import Any

import zxingcpp
from PIL import Image

from plom.common.tpv_utils import (
    parseTPV,
    parseExtraPageCode,
    getPaperPageVersion,
    isValidTPV,
    isValidExtraPageCode,
    isValidScrapPaperCode,
    isValidBundleSeparatorPaperCode,
)

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
        rotation: Rotate the image by 90, -90, 180 or 270 degrees
            counterclockwise prior to reading the QR codes. Defaults to 0.

    Returns:
        A dict with keys such as "NW", "NE", "SW", "SE", "other1", "other2",
        each with a dict containing
        'raw_qr_string', 'x', 'y' (the horizontal and vertical pixel coordinates
        of the QR code), 'orientation' (the rotation ccw of the QR code in degrees,
        currently an integer) and other info.
        Any QR codes that aren't roughly in a corner will appear with keys
        "other1", "other2", etc.
        If two or more QR codes are in the same broadly-defined corner, say SW,
        then if one of them is a proper QR code identified as a "qr_page"
        (i.e., not an error and not a microQR), then that one is set to the SW
        corner (and the others join the others list).  In all other cases,
        we refuse to choose a SW corner one and dump everything in the others
        list.
    """
    valid_corners = ("NW", "NE", "SW", "SE")
    qr_list_by_corner: dict[str, list[dict[str, Any]]] = {k: [] for k in valid_corners}

    cornerQR: dict[str, Any] = {}

    qrlist = QRextract_list(image, rotation=rotation)
    # first build a list for each corner
    other_list = []
    for qr in qrlist:
        corner = qr["corner_guess_from_position"]
        if corner in valid_corners:
            qr_list_by_corner[corner].append(qr)
        else:
            other_list.append(qr)

    for k, qrs in qr_list_by_corner.items():
        if len(qrs) == 0:
            pass
        elif len(qrs) == 1:
            cornerQR[k] = qrs[0]
        else:
            # separate the "qr_pages" from the microQR stuff
            qr_pages = [qr for qr in qrs if qr["page_type"] == "plom_qr"]
            if len(qr_pages) == 1:
                # if there is exactly qr_page, keep that
                cornerQR[k] = qr_pages[0]
                # and put the rest into the "other" list
                for qr in qrs:
                    if qr["page_type"] != "plom_qr":
                        other_list.append(qr)
            else:
                for qr in qrs:
                    other_list.append(qr)

    c = 0
    for qr in other_list:
        c += 1
        cornerQR[f"other{c}"] = qr
    return cornerQR


def QRextract_list(image, *, rotation: int = 0) -> list[dict[str, Any]]:
    """Decode the QR codes in an image."""
    if not isinstance(image, Image.Image):
        image = pil_load_with_jpeg_exif_rot_applied(image)

    if rotation != 0:
        assert rotation in (-90, 90, 270, 180)
        image = image.rotate(rotation, expand=True)

    # PIL does lazy loading.  Force loading now so we see errors now.
    # Otherwise, zxing-cpp might hide error messages, Issue #2597
    image.load()

    # TODO: new kwargs?  only_QRCodeModel2, only_MicroQRCode?

    # qr_code_formats = (
    #     zxingcpp.BarcodeFormat.QRCodeModel2,
    #     zxingcpp.BarcodeFormat.MicroQRCode,
    # )

    # deprecated?  but mypy complains about the the above...?
    qr_code_formats = (
        zxingcpp.BarcodeFormat.QRCodeModel2 | zxingcpp.BarcodeFormat.MicroQRCode
    )

    qrlist = zxingcpp.read_barcodes(image, formats=qr_code_formats)
    list_of_dicts = []
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
            "x_coord": x_coord,
            "y_coord": y_coord,
            "orientation": -qr.orientation,  # Zxing has + meaning cw (!)
            "corner_guess_from_position": _findCorner(x_coord, y_coord, image.size),
        }
        d.update(_parse_raw_qr_string(qr.text))
        list_of_dicts.append(d)
    return list_of_dicts


def _parse_raw_qr_string(raw_qr_string: str) -> dict[str, Any]:
    """Extract Plom-specific info in a dict structure from a raw QR code string."""
    if isValidTPV(raw_qr_string):
        paper_id, page_num, version_num, public_code, corner = parseTPV(raw_qr_string)
        # get the "TTTTTPPPVV" part
        tpv = getPaperPageVersion(raw_qr_string)
        return {
            "page_type": "plom_qr",
            "page_info": {
                "paper_id": paper_id,
                "page_num": page_num,
                "version_num": version_num,
                "public_code": public_code,
            },
            "quadrant": corner,
            "tpv": tpv,
        }

    elif isValidExtraPageCode(raw_qr_string):
        corner = parseExtraPageCode(raw_qr_string)
        return {
            "page_type": "plom_extra",
            "quadrant": corner,
            "tpv": "plomX",
        }

    elif isValidScrapPaperCode(raw_qr_string):
        corner = parseExtraPageCode(raw_qr_string)
        return {
            "page_type": "plom_scrap",
            "quadrant": corner,
            "tpv": "plomS",
        }

    elif isValidBundleSeparatorPaperCode(raw_qr_string):
        corner = parseExtraPageCode(raw_qr_string)
        return {
            "page_type": "plom_bundle_separator",
            "quadrant": corner,
            "tpv": "plomB",
        }

    else:
        return {
            "page_type": "invalid_qr",
            "quadrant": "0",
        }
