# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.
"""

__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer, Colin Macdonald and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

specdir = "specAndDatabase"
from .specParser import SpecVerifier, SpecParser
from .version import __version__

Plom_API_Version = "22"  # bumped for getImages api change
Default_Port = 41984

# Image types we expect the client to be able to handle, in lowercase
# TODO: think about JBIG, etc: other stuff that commonly lives in PDF
PlomImageExts = ("png", "jpg", "jpeg")

ScenePixelHeight = 2000

# in points; absolute not relative to the above, TODO: should redo in absolute scale
AnnFontSizePts = 24.0

from .rules import isValidStudentNumber
