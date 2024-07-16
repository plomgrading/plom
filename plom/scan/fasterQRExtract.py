# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image

from .rotate import pil_load_with_jpeg_exif_rot_applied

# hide import inside function to prevent PlomClient depending on it
# from zxingcpp import read_barcodes, BarcodeFormat


def findCorner(qr, dim):
    """Determines the x-y coordinates and relative location of the given QR code's approximate centre.

    Args:
        qr (zxingcpp.Result): object containing the information stored in the QR code
        dim (tuple): pair of ints that correspond to the dimensions of
            the image that contains the QR code.

    Returns:
        tuple: a triple ``(str, mx, my)`` where ``str`` is a 2-char string, one of
        "NE", "NE", "SW", "SE", depending on the relative location of the QR code,
        or "??" if the QR code cannot be detected. ``mx, my`` are either ints that correspond
        to the (x, y) coordinates of the QR code's centre location in the image, or None
        if the QR code is not detected and there are no coordinates to return.
    """
    qr_polygon = [
        qr.position.top_left,
        qr.position.top_right,
        qr.position.bottom_left,
        qr.position.bottom_right,
    ]
    mx = mean([p.x for p in qr_polygon])
    my = mean([p.y for p in qr_polygon])
    width, height = dim

    NS = "?"
    EW = "?"
    if my < 0.4 * height:
        NS = "N"
    elif my > 0.6 * height:
        NS = "S"
    else:
        return "??", None, None
    if mx < 0.4 * width:
        EW = "W"
    elif mx > 0.6 * width:
        EW = "E"
    else:
        return "??", None, None
    return NS + EW, mx, my


def QRextract(
    image, *, try_harder: bool = True, rotation: int = 0
) -> dict[str, dict[str, Any]]:
    """Decode and return QR codes in an image.

    Args:
        image (str/pathlib.Path/PIL.Image): an image filename, either in
            the local dir or specified e.g., using `pathlib.Path`.  Can
            also be an instance of Pillow's `Image`.

    Keyword Args:
        try_harder (bool): Try to find QRs on a smaller resolution.
            Defaults to True.  Sometimes this seems work around high
            failure rates in the synthetic images used in CI testing.
            Details below.
        rotation (int): Rotate the image by 90, -90, 180 or 270 degrees
            counterclockwise prior to reading the QR codes. Defaults to 0.

    Returns:
        A dict with keys "NW", "NE", "SW", "SE", each with a dict containing
        a 'tpv_signature', 'x', 'y' keys that correspond to strings extracted from
        QR codes (one string per code) and the x-y coordinates of the QR code.
        The dict is empty if no QR codes found in that corner.

    Without the `try_harder` flag, we observe high failure rates when
    the vertical resolution is near 2000 pixels (our current default).
    This is Issue #967 [1].  It is not prevalent in real-life images,
    but causes a roughly 5%-10% failure rate in our synthetic CI runs.
    The workaround (on by default) uses Pillow's `.reduce()` to quickly
    downscale the image.  This does increase the run time (have not
    checked by how much: I assume between 25% and 50%) so if that is
    more of a concern than error rate, turn off this flag.

    [1] https://gitlab.com/plom/plom/-/issues/967
    """
    # hide import inside function to prevent PlomClient depending on it
    from zxingcpp import read_barcodes, BarcodeFormat

    cornerQR: dict[str, dict[str, Any]] = {"NW": {}, "NE": {}, "SW": {}, "SE": {}}

    if not isinstance(image, Image.Image):
        image = pil_load_with_jpeg_exif_rot_applied(image)

    if rotation != 0:
        assert rotation in (-90, 90, 270, 180)
        image = image.rotate(rotation, expand=True)

    # PIL does lazy loading.  Force loading now so we see errors now.
    # Otherwise, zxing-cpp might hide error messages, Issue #2597
    image.load()

    try:
        micro = BarcodeFormat.MicroQRCode
    except AttributeError:
        # workaround github.com/zxing-cpp/zxing-cpp/issues/512
        micro = BarcodeFormat.MircoQRCode

    qrlist = read_barcodes(image, formats=(BarcodeFormat.QRCode | micro))
    for qr in qrlist:
        cnr, x_coord, y_coord = findCorner(qr, image.size)
        if cnr in cornerQR.keys():
            cornerQR[cnr].update({"tpv_signature": qr.text, "x": x_coord, "y": y_coord})

    if try_harder:
        # Try again on smaller image: originally for pyzbar (Issue #967), but I
        # think I've seen this find a QR-code missed by the above since
        # switching to ZXing-cpp (Issue #2520), so we'll leave it.
        try:
            image = image.reduce(2)
        except ValueError:
            # mode-P (paletted pngs) fail to reduce, Issue #2631
            qrlist = []
        else:
            qrlist = read_barcodes(image, formats=(BarcodeFormat.QRCode | micro))
        for qr in qrlist:
            cnr, x_coord, y_coord = findCorner(qr, image.size)
            if cnr in cornerQR.keys():
                s = qr.text
                prev_tpv_signature = cornerQR[cnr].get("tpv_signature")
                if not prev_tpv_signature:
                    # TODO: log these failures?
                    # print(
                    #     f'Found QR-code "{s}" at {cnr} on reduced image, '
                    #     "not found at original size"
                    # )
                    cornerQR[cnr].update(
                        {"tpv_signature": s, "x": x_coord, "y": y_coord}
                    )
                elif s == prev_tpv_signature:
                    # no-op, we already read this at the previous resolution
                    pass
                else:
                    # TODO: found a different QR code at lower resolution!
                    # For now, just ignore and keep the previous hires result
                    pass

    return cornerQR


def QRextract_legacy(
    image, *, write_to_file: bool = True, try_harder: bool = True
) -> dict[str, list[str]] | None:
    """Decode QR codes in an image, return or save them in .qr file.

    Args:
        image (str/pathlib.Path/PIL.Image): an image filename, either in
            the local dir or specified e.g., using `pathlib.Path`.  Can
            also be an instance of Pillow's `Image`.

    Keyword Args:
        write_to_file (bool): by default, the results are written into
            a file named `image.qr` (i.e., the same as input name
            with `.qr` appended, so something like `foo.jpg.qr`).
            If this `.qr` file already exists and is non-empty, then no
            action is taken, and None is returned.
        try_harder (bool): Try to find QRs on a smaller resolution.
            Defaults to True.  Sometimes this seems work around high
            failure rates in the synthetic images used in CI testing.
            Details blow.

    Returns:
        dict/None: Keys "NW", "NE", "SW", "SE", each with a list of the
            strings extracted from QR codes, one string per code.  The
            list is empty if no QR codes found in that corner.

    Without the `try_harder` flag, we observe high failure rates when
    the vertical resolution is near 2000 pixels (our current default).
    This is Issue #967 [1].  It is not prevalent in real-life images,
    but causes a roughly 5%-10% failure rate in our synthetic CI runs.
    The workaround (on by default) uses Pillow's `.reduce()` to quickly
    downscale the image.  This does increase the run time (have not
    checked by how much: I assume between 25% and 50%) so if that is
    more of a concern than error rate, turn off this flag.

    [1] https://gitlab.com/plom/plom/-/issues/967
    """
    # hide import inside function to prevent PlomClient depending on it
    from zxingcpp import read_barcodes, BarcodeFormat

    if write_to_file:
        image = Path(image)
        # foo.jpg to foo.jpg.qr
        qrfile = image.with_suffix("{}.qr".format(image.suffix))
        if qrfile.exists() and qrfile.stat().st_size > 0:
            return None

    cornerQR: dict[str, list[str]] = {"NW": [], "NE": [], "SW": [], "SE": []}

    if not isinstance(image, Image.Image):
        image = pil_load_with_jpeg_exif_rot_applied(image)

    # PIL does lazy loading.  Force loading now so we see errors now.
    # Otherwise, zxing-cpp might hide error messages, Issue #2597
    image.load()

    try:
        micro = BarcodeFormat.MicroQRCode
    except AttributeError:
        # workaround github.com/zxing-cpp/zxing-cpp/issues/512
        micro = BarcodeFormat.MircoQRCode

    qrlist = read_barcodes(image, formats=(BarcodeFormat.QRCode | micro))
    for qr in qrlist:
        cnr = findCorner(qr, image.size)[0]
        if cnr in cornerQR.keys():
            cornerQR[cnr].append(qr.text)

    if try_harder:
        # try again on smaller image: avoids random CI failures #967?
        image = image.reduce(2)
        qrlist = read_barcodes(image, formats=(BarcodeFormat.QRCode | micro))
        for qr in qrlist:
            cnr = findCorner(qr, image.size)[0]
            if cnr in cornerQR.keys():
                s = qr.text
                if s not in cornerQR[cnr]:
                    # TODO: log these failures?
                    # print(
                    #     f'Found QR-code "{s}" at {cnr} on reduced image, '
                    #     "not found at original size"
                    # )
                    cornerQR[cnr].append(s)

    if write_to_file:
        with open(qrfile, "w") as fh:
            json.dump(cornerQR, fh)

    return cornerQR
