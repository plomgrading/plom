__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import os
import shutil
import subprocess
import sys
import tempfile

# Take the png file name as argument.
imgName = sys.argv[1]
# Get the current directory
curDir = os.getcwd()

# First check if the image is in portrait or landscape by aspect ratio
# Should be in portrait.
cmd = ["identify", "-format", "%[fx:w/h]", imgName]
ratio = subprocess.check_output(cmd).decode().rstrip()
if float(ratio) > 1:  # landscape
    subprocess.check_call(["mogrify", "-quiet", "-rotate", "90", imgName])

# Operate in a temp directory
with tempfile.TemporaryDirectory() as tmpDir:
    # copy image to temp directory and then chdir there
    shutil.copy(imgName, tmpDir)
    os.chdir(tmpDir)

    # split image into pieces, then extract qr codes from corners
    # this helps to determine the orientation
    # TODO: can tell diff b/w odd/even: doc somewhere?
    cmd = ["convert", "-quiet", imgName, "-crop", "4x5@", "tile_%d.png"]
    subprocess.check_call(cmd)

    # Use zbarimg to extract QR codes from some tiles
    # There may not be any (e.g., DNW area, folded corner, poor quality)
    cornerQR = {}
    cornerKeys = ["NE", "NW", "SW", "SE"]
    cornerTiles = ["tile_3.png", "tile_0.png", "tile_16.png", "tile_19.png"]
    for i in range(0, 4):
        # Apply a slight blur filter to make reading codes easier (typically)
        subprocess.check_call(
            ["mogrify", "-quiet", cornerTiles[i], "-blur", "0", "-quality", "100"],
        )
        try:
            cmd = ["zbarimg", "-q", "-Sdisable", "-Sqr.enable", cornerTiles[i]]
            this = subprocess.check_output(cmd).decode().rstrip().split("\n")
        except subprocess.CalledProcessError as zberr:
            if zberr.returncode == 4:  # means no codes found
                this = []
            else:
                raise
        cornerQR[cornerKeys[i]] = this

    # go back to original directory
    os.chdir(curDir)
    # dump the output of zbarimg into blah.png.qr
    with open("{}.qr".format(imgName), "w") as fh:
        # TODO: or pickle or json
        fh.write(repr(cornerQR))
