__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import json
import os
from pyzbar.pyzbar import decode
from PIL import Image
import subprocess
import sys


def findCorner(qr, dim):
    xc = []
    yc = []
    for p in qr.polygon:
        xc.append(p.x)
        yc.append(p.y)
    mx = sum(xc) / len(xc)
    my = sum(yc) / len(yc)

    NS = "?"
    EW = "?"
    if my < dim[1] * 0.3:
        NS = "N"
    elif my > dim[1] * 0.7:
        NS = "S"
    else:
        return "??"
    if mx < dim[0] * 0.3:
        EW = "W"
    elif mx > dim[0] * 0.7:
        EW = "E"
    else:
        return "??"
    return NS + EW


# Take the png file name as argument.
imgName = sys.argv[1]
# First check if the image is in portrait or landscape by aspect ratio
# Should be in portrait.
cmd = ["identify", "-format", "%[fx:w/h]", imgName]
ratio = subprocess.check_output(cmd).decode().rstrip()
if float(ratio) > 1:  # landscape
    subprocess.check_call(["mogrify", "-quiet", "-rotate", "90", imgName])

cornerQR = {"NW": [], "NE": [], "SW": [], "SE": []}

img = Image.open(imgName)
qrlist = decode(img)
for qr in qrlist:
    cnr = findCorner(qr, img.size)
    if cnr in ["NW", "NE", "SW", "SE"]:
        cornerQR[cnr].append(qr.data.decode())

with open("{}.qr".format(imgName), "w") as fh:
    json.dump(cornerQR, fh)
