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

    # split image into five pieces, then extract qr codes from top and bottom.
    # this helps to determine the orientation
    os.system("convert -quiet {} -crop 1x5@ tile_%d.png".format(imgName))
    # We only care about the top and bottom fifths
    # There should not be QR codes near the middle.
    # Apply a slight blur filter to make reading codes easier (typically)
    os.system("mogrify -quiet tile_0.png -blur 0 -quality 100")
    os.system("mogrify -quiet tile_4.png -blur 0 -quality 100")
    try:
        # Run zbarimg on top fifth
        # Extract the output (if any) and store in "up"
        up = (
            subprocess.check_output(
                ["zbarimg", "-q", "-Sdisable", "-Sqr.enable", "tile_0.png"]
            )
            .decode()
            .rstrip()
            .split("\n")
        )
    except subprocess.CalledProcessError as zberr:
        if zberr.returncode == 4:  # means no codes found
            up = []
        else:  # some other error
            print("Zbarimg error processing file {}".format(imgName))
        # Run zbarimg on bottom fifth
        # Extract the output (if any) and store in "down"
    try:
        down = (
            subprocess.check_output(
                ["zbarimg", "-q", "-Sdisable", "-Sqr.enable", "tile_4.png"]
            )
            .decode()
            .rstrip()
            .split("\n")
        )
    except subprocess.CalledProcessError as zberr:
        if zberr.returncode == 4:  # means no codes found
            down = []
        else:  # some other error
            print("Zbarimg error processing file {}".format(imgName))
    both = set(up + down)
    # go back to original directory
    os.chdir(curDir)
    # dump the output of zbarimg into blah.png.qr
    with open("{}.qr".format(imgName), "w") as fh:
        for X in both:
            fh.write("{}\n".format(X))
    # there should be 1 qr code in top half and 2 in bottom half
    # if not then flip the image.
    if len(up) > len(down):
        os.system("mogrify -quiet -rotate 180 {}".format(imgName))
