# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.

This is the Plom Server.
"""

__copyright__ = "Copyright (C) 2018-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

# Also in plom/__init__.py
__version__ = "0.18.1.dev0"

Plom_API_Version = "114"

__all__ = [
    "Preparation",
    "BuildPaperPDF",
    "Papers",
    "Preparation",
    "Scan",
    "SpecCreator",
]
