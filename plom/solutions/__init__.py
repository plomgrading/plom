# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2024 Colin B. Macdonald

"""Plom tools associated with uploading/downloading solutions."""

__copyright__ = "Copyright (C) 2020-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from plom import __version__

from plom.finish import clear_manager_login
from plom.create import with_manager_messenger
from plom.solutions.deleteSolutionImage import deleteSolutionImage
from plom.solutions.putSolutionImage import putSolutionImage
from plom.solutions.putSolutionImage import putExtractedSolutionImages
from plom.solutions.getSolutionImage import getSolutionImage
from plom.solutions.checkSolutionStatus import checkStatus
from plom.solutions.extractSolutions import extractSolutionImages


# what you get from "from plom.solutions import *"
__all__ = [
    "getSolutionImage",
    "putSolutionImage",
    "putExtractedSolutionImages",
    "deleteSolutionImage",
    "extractSolutionImages",
    "checkStatus",
    "clear_manager_login",
]
