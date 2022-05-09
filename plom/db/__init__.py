# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Colin B. Macdonald

"""Plom database stuff."""

__copyright__ = "Copyright (C) 2018-2022 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from .examDB import PlomDB
from .buildPlomDB import initialiseExamDatabaseFromSpec

__all__ = [
    "initialiseExamDatabaseFromSpec",
    "PlomDB",
]
