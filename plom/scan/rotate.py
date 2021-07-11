# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

import os
import subprocess
from warnings import warn

try:
    import jpegtran

    have_jpegtran = True
except ImportError:
    warn("jpegtran-cffi package not available: jpeg rotations will be lossy")
    have_jpegtran = False


def rotateBitmap(fname, angle):
    """Rotate bitmap, (almost) lossless for jpg.

    args:
        filename (str): name of a file
        angle (int): 0, 90, 180, 270, or -90 degree rotation.

    If available, this routine uses the `jpegtran-cffi` library for
    lossless jpeg rotations.  If that library is not available, there
    will be a loss of quality when rotating a jpeg image.

    TODO: think about multiples of 8/16 thing for jpeg.
    """
    assert angle in (0, 90, 180, 270, -90), "Invalid rotation angle {}".format(angle)
    if angle == 0:
        return
    fnamebase, fnameext = os.path.splitext(fname)
    if fnameext.lower() in (".jpg", ".jpeg"):
        if have_jpegtran:
            print("**** Doing JPEG rotation {} on {}".format(angle, fname))
            im = jpegtran.JPEGImage(fname)
            im.rotate(angle).save(fname)
            return
        warn(
            f"Doing LOSSY jpeg rotation {angle} on {fname} [b/c jpegtran-cffi not installed]"
        )

    subprocess.run(
        ["mogrify", "-quiet", "-rotate", str(angle), fname],
        stderr=subprocess.STDOUT,
        shell=False,
        check=True,
    )
