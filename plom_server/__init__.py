# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2026 Colin B. Macdonald

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.

This is the Plom Server.
"""

__copyright__ = "Copyright (C) 2018-2026 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

# Also in plom/common.py
__version__ = "0.20.2.dev0"

# The API and the database are versioned to give a quick way to address compatibility.
# There is no reason that they must match, although we generally bump both for the first
# release 0.x.0.  Both should not change during patches of the 0.x.y cycle.  That is our
# practice as of early 2026.  TODO: why is API_Version a string?
Plom_API_Version = "116"
Plom_DB_Version = 116

# __all__ = [
#     "Preparation",
#     "BuildPaperPDF",
#     "Papers",
#     "Preparation",
#     "Scan",
#     "SpecCreator",
# ]
