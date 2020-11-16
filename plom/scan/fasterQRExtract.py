# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import json
import os
import sys
from statistics import mean

from pyzbar.pyzbar import decode
from PIL import Image


def findCorner(qr, dim):
    mx = mean([p.x for p in qr.polygon])
    my = mean([p.y for p in qr.polygon])
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


def QRextract(image_name, write_to_file=True):
    """Decode QR codes in an image, return or save them in .qr file.

    args:
        image_name (str/pathlib.Path): an image file, either in local
            dir or specified e.g., using `pathlib.Path`.
        write_to_file (bool): by default, the results are written into
            a file named `img_name.qr` (i.e., the same as input name
            with `.qr` appended, so something like `foo.jpg.qr`).

    returns:
        dict: Keys "NW", "NE", "SW", "SE", which with a list of the
            strings extracted from QR codes, one string per code.
    """

    if write_to_file:
        qrname = "{}.qr".format(image_name)
        if os.path.exists(qrname) and os.path.getsize(qrname) != 0:
            return

    cornerQR = {"NW": [], "NE": [], "SW": [], "SE": []}

    img = Image.open(image_name)
    qrlist = decode(img)
    for qr in qrlist:
        cnr = findCorner(qr, img.size)
        if cnr in cornerQR.keys():
            cornerQR[cnr].append(qr.data.decode())

    if write_to_file:
        with open(qrname, "w") as fh:
            json.dump(cornerQR, fh)
    return cornerQR


if __name__ == "__main__":
    # Take the bitmap file name as argument.
    imgName = sys.argv[1]
    QRextract(imgName)
