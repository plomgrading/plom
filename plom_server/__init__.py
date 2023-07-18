# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

"""Plom is Paperless Open Marking.

Plom creates multi-versioned tests, scans them, coordinates online
marking/grading, and returns them online.

This is the Plom Server.
"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

# Also hardcoded in AppImageBuilder.yml and deprecated in plom/version.py
__version__ = "0.14.0.dev0"

# import Web_Plom

__all__ = ["Web_Plom"]
