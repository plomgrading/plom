# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Vala Vakilian

"""Plom tools for producing papers"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from pathlib import Path

from plom import __version__

paperdir = Path("papersToPrint")

from .buildClasslist import possible_surname_fields, possible_given_name_fields
from .upload_classlist import get_messenger
from .buildDatabaseAndPapers import build_database, build_papers

from .buildClasslist import process_classlist_file, get_demo_classlist
from .upload_classlist import upload_classlist, upload_demo_classlist

from .faketools import make_scribbles
from .hwFaker import make_hw_scribbles

# what you get from "from plom.produce import *"
__all__ = [
    "get_demo_classlist",
    "process_classlist_file",
    "upload_classlist",
    "upload_demo_classlist",
    "make_scribbles",
    "make_hw_scribbles",
]
