# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Colin B. Macdonald

import os
import subprocess

import jpegtran


def rotateBitmap(fname, angle):
    """Rotate bitmap, (almost) lossless for jpg.

    args:
        filename (str): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    TODO: think about multiples of 8/16 thing for jpeg.
    """
    assert angle in (0, 90, 180, 270, -90), "Invalid rotation angle {}".format(angle)
    if angle == 0:
        return
    fnamebase, fnameext = os.path.splitext(fname)
    if fnameext.lower() in (".jpg", ".jpeg"):
        print("**** Doing JPEG rotation {} on {}".format(angle, fname))
        im = jpegtran.JPEGImage(fname)
        im.rotate(angle).save(fname)
        return

    subprocess.run(
        ["mogrify", "-quiet", "-rotate", str(angle), fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )
