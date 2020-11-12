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


def QRextract(imgName):
    """Decode qr codes from an image file, save them in .qr file.

    args:
        imgName (str/pathlib.Path): an image file, either in local dir
            or specified e.g., using `pathlib.Path`.

    returns:
        dict: Keys "NW", "NE", "SW", "SE", which with a list of the
            strings extracted from QR codes, one string per code.

    Currently, the results are written into a `imgName.qr` file (same
    as input file with `.qr` appended), but this could change in the
    future.

    TODO: currently this does not check if the QR codes are Plom codes:
    e.g., some Android scanning apps place a QR code on each page.
    Perhaps we should discard non-Plom codes before we look for corners?
    """

    qrname = "{}.qr".format(imgName)
    if os.path.exists(qrname) and os.path.getsize(qrname) != 0:
        return

    cornerQR = {"NW": [], "NE": [], "SW": [], "SE": []}

    img = Image.open(imgName)
    qrlist = decode(img)
    for qr in qrlist:
        cnr = findCorner(qr, img.size)
        if cnr in cornerQR.keys():
            cornerQR[cnr].append(qr.data.decode())

    with open(qrname, "w") as fh:
        json.dump(cornerQR, fh)
    return cornerQR


if __name__ == "__main__":
    # Take the bitmap file name as argument.
    imgName = sys.argv[1]
    QRextract(imgName)
