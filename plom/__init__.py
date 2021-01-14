# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.
"""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import sys

if sys.version_info[0] == 2:
    raise RuntimeError("Plom requires Python 3; it will not work with Python 2")

from .specVerifier import SpecVerifier, specdir
from .version import __version__

Plom_API_Version = "25"
Default_Port = 41984

# Image types we expect the client to be able to handle, in lowercase
# TODO: think about JBIG, etc: other stuff that commonly lives in PDF
PlomImageExts = ("png", "jpg", "jpeg")

ScenePixelHeight = 2000

# in points; absolute not relative to the above, TODO: should redo in absolute scale
AnnFontSizePts = 24.0

from .rules import isValidStudentNumber
