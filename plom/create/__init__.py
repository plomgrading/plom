# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Vala Vakilian

"""Plom tools related to producing papers, and setting up servers."""

__copyright__ = "Copyright (C) 2019-2022 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from pathlib import Path

from plom import __version__

paperdir = Path("papersToPrint")

from .start_messenger import start_messenger
from plom.finish import clear_manager_login

from .buildClasslist import possible_surname_fields, possible_given_name_fields
from .buildDatabaseAndPapers import build_database, build_papers

from .buildClasslist import process_classlist_file, get_demo_classlist
from .upload_classlist import upload_classlist, upload_demo_classlist

from .push_pull_rubrics import upload_demo_rubrics
from .push_pull_rubrics import upload_rubrics_from_file, download_rubrics_to_file

from .version_map_from_csv import version_map_from_csv

from .scribble_utils import make_scribbles
from .scribble_hw_utils import make_hw_scribbles

# what you get from "from plom.create import *"
__all__ = [
    "clear_manager_login",
    "get_demo_classlist",
    "process_classlist_file",
    "upload_classlist",
    "upload_demo_classlist",
    "make_scribbles",
    "make_hw_scribbles",
    "upload_demo_rubrics",
    "upload_rubrics_from_file",
    "download_rubrics_to_file",
]