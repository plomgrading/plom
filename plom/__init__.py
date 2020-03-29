# -*- coding: utf-8 -*-

"""
Plom is PaperLess Open Marking.  TODO: Insert longer blurb
"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from .specParser import SpecVerifier, SpecParser
from .version import __version__, Plom_API_Version
from .version import Default_Port

from .rules import isValidStudentNumber
specdir = "specAndDatabase"
