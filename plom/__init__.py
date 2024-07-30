# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Aden Chan

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.
"""

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

# Also hardcoded in AppImageBuilder.yml
__version__ = "0.15.6"

import sys

if sys.version_info[0] == 2:
    raise RuntimeError("Plom requires Python 3; it will not work with Python 2")

from .specVerifier import SpecVerifier, specdir, get_question_label

Plom_API_Version = "109"
Plom_Legacy_Server_API_Version = "60"
Default_Port = 41984

# Image types we expect the client to be able to handle, in lowercase
# TODO: think about JBIG, etc: other stuff that commonly lives in PDF
PlomImageExts = ("png", "jpg", "jpeg")

# TODO: this should be a default and the PageScene should have a physical size.
ScenePixelHeight = 2000

from .rules import isValidStudentID

from .version_maps import undo_json_packing_of_version_map
from .version_maps import make_random_version_map, check_version_map
from .version_maps import version_map_from_file, version_map_to_csv

from .tagging import (
    is_valid_tag_text,
    plom_valid_tag_text_pattern,
    plom_valid_tag_text_description,
)

# TODO: what you get from "from plom import *"
# __all__ = ["client", "server", "produce", "scan", "finish", "manager"]
