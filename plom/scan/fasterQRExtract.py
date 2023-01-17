# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

import json
from pathlib import Path
from statistics import mean

# use this to replace pyzbar - since it handles micro-qr-codes
from zxingcpp import read_barcodes, BarcodeFormats, BarcodeFormat

from PIL import Image


def findCorner(qr, dim):
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
        return "??"
    if mx < 0.4 * width:
        EW = "W"
    elif mx > 0.6 * width:
        EW = "E"
    else:
        return "??"
    return NS + EW


def QRextract(image, write_to_file=True, try_harder=True):
    """Decode QR codes in an image, return or save them in .qr file.

    args:
        image (str/pathlib.Path/PIL.Image): an image filename, either in
            the local dir or specified e.g., using `pathlib.Path`.  Can
            also be an instance of Pillow's `Image`.
        write_to_file (bool): by default, the results are written into
            a file named `image.qr` (i.e., the same as input name
            with `.qr` appended, so something like `foo.jpg.qr`).
            If this `.qr` file already exists and is non-empty, then no
            action is taken, and None is returned.
        try_harder (bool): Try to find QRs on a smaller resolution.
            Defaults to True.  Sometimes this seems work around high
            failure rates in the synthetic images used in CI testing.
            Details blow.

    returns:
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

    TODO: this issue should be reported to the ZBar project.

    Here are the results of an experiment shows the failure rate without
    this fix:

    vertical dim | failure rate
    -------------|-------------
    1600         | 0%
    1900         | 0%
    1950         | 7%
    1998         | 2%
    1999         | 5%
    2000         | 29%
    2001         | 1%
    2002         | 23%
    2003         | 17%
    2004         | 8%
    2005         | 23%
    2010         | 3%
    2100         | 1%
    3000         | 0%

    [1] https://gitlab.com/plom/plom/-/issues/967
    """
    if write_to_file:
        image = Path(image)
        # foo.jpg to foo.jpg.qr
        qrfile = image.with_suffix("{}.qr".format(image.suffix))
        if qrfile.exists() and qrfile.stat().st_size > 0:
            return None

    cornerQR = {"NW": [], "NE": [], "SW": [], "SE": []}

    if not isinstance(image, Image.Image):
        image = Image.open(image)

    qrlist = read_barcodes(
        image, formats=(BarcodeFormat.QRCode | BarcodeFormat.MircoQRCode)
    )
    for qr in qrlist:
        cnr = findCorner(qr, image.size)
        if cnr in cornerQR.keys():
            cornerQR[cnr].append(qr.text)

    if try_harder:
        # try again on smaller image: avoids random CI failures #967?
        image = image.reduce(2)
        qrlist = read_barcodes(
            image, formats=(BarcodeFormat.QRCode | BarcodeFormat.MircoQRCode)
        )
        for qr in qrlist:
            cnr = findCorner(qr, image.size)
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
