# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import json
import os
import subprocess
import sys
from statistics import mean

from pyzbar.pyzbar import decode
from PIL import Image

from plom.scan import rotateBitmap


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

    Currently, those are written into a `imgName.qr` file but this could
    change in the future.  TODO: document whether `imgName` is a full path
    or just a filename and where the `.qr` file gets written.
    """
    qrname = "{}.qr".format(imgName)
    if os.path.exists(qrname) and os.path.getsize(qrname) != 0:
        return

    # First check if the image is in portrait or landscape by aspect ratio
    # Should be in portrait.
    cmd = ["identify", "-format", "%[fx:w/h]", imgName]
    ratio = subprocess.check_output(cmd).decode().rstrip()
    if float(ratio) > 1:  # landscape
        rotateBitmap(imgName, 90)

    cornerQR = {"NW": [], "NE": [], "SW": [], "SE": []}

    img = Image.open(imgName)
    qrlist = decode(img)
    for qr in qrlist:
        cnr = findCorner(qr, img.size)
        if cnr in ["NW", "NE", "SW", "SE"]:
            cornerQR[cnr].append(qr.data.decode())

    with open(qrname, "w") as fh:
        json.dump(cornerQR, fh)


if __name__ == "__main__":
    # Take the bitmap file name as argument.
    imgName = sys.argv[1]
    QRextract(imgName)
