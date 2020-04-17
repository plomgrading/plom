# -*- coding: utf-8 -*-

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess

import jpegtran


def rotateBitmap(fname, angle):
    """Rotate bitmap, (almost) lossless for jpg.

    args:
        filename (str): name of a file
        angle (int): 90, 180, or 270 degree rotation

    TODO: think about multiples of 8/16 thing for jpeg.
    """
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
