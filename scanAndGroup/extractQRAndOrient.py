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
try:
    ratio = (
        subprocess.check_output(["identify", "-format", "%[fx:w/h]", imgName])
        .decode()
        .rstrip()
    )
    # if ratio>1 then in landscape so rotate.
    if float(ratio) > 1:
        os.system("mogrify -quiet -rotate 90 {}".format(imgName))
except subprocess.CalledProcessError:
    print("Imagemagick error getting aspect ratio")

# Operate in a temp directory
with tempfile.TemporaryDirectory() as tmpDir:
    # copy image to temp directory and then chdir there
    shutil.copy(imgName, tmpDir)
    os.chdir(tmpDir)

    # split image into pieces, then extract qr codes from corners
    # this helps to determine the orientation
    # TODO: can tell diff b/w odd/even: doc somewhere?
    os.system("convert -quiet {} -crop 4x5@ tile_%d.png".format(imgName))

    # Use zbarimg to extract QR codes from some tiles
    # There may not be any (e.g., DNW area, folded corner, poor quality)
    cornerQR = {}
    cornerKeys = ['NE', 'NW', 'SW', 'SE']
    cornerTiles = ['tile_3.png', 'tile_0.png', 'tile_16.png', 'tile_19.png']
    for i in range(0, 4):
        # Apply a slight blur filter to make reading codes easier (typically)
        subprocess.run(
            ["mogrify", "-quiet", cornerTiles[i], "-blur", "0", "-quality", "100"],
            stderr=subprocess.STDOUT, shell=False, check=True)
        try:
            this = (subprocess.check_output(
                    ["zbarimg", "-q", "-Sdisable", "-Sqr.enable", cornerTiles[i]]
                )
                .decode()
                .rstrip()
                .split("\n")
            )
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

    # TODO: refactor later to just keep cornerQR: info in the ordering
    # TODO: we should orient after we are sure these are the correct QR
    # there should be 1 qr code in top half and 2 in bottom half
    up = cornerQR['NE'] + cornerQR['NW']
    down = cornerQR['SW'] + cornerQR['SE']
    if len(up) == 1 and len(down) == 2:
        pass
    elif len(up) == 2:
        # if its opposite then flip the image.
        os.system("mogrify -quiet -rotate 180 {}".format(imgName))
    else:
        # TODO: should mark orientation as "unknown", for
        # manualPageIdentifier to deal with.  For now, the incorrect
        # number of QR codes will cause this to be flagged for manual
        # processing.  But later that will be merely a warning.
        # https://gitlab.math.ubc.ca/andrewr/MLP/issues/272
        pass
