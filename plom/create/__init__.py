# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Edith Coates

"""Plom tools related to producing papers, and setting up servers."""

__copyright__ = "Copyright (C) 2019-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from pathlib import Path

from plom import __version__

paperdir = Path("papersToPrint")

from .start_messenger import start_messenger, with_manager_messenger
from .start_messenger import clear_manager_login

from .buildDatabaseAndPapers import build_database, build_papers
from .mergeAndCodePages import make_PDF
from .build_extra_page_with_qrcodes import build_extra_page_pdf
from .build_scrap_paper_with_qrcodes import build_scrap_paper_pdf

from .classlistValidator import (
    sid_field,
    fullname_field,
    papernumber_field,
    PlomClasslistValidator,
)
from .buildClasslist import process_classlist_file, get_demo_classlist
from .upload_classlist import upload_classlist, upload_demo_classlist

from .status import status

from .push_pull_rubrics import upload_rubrics, download_rubrics
from .push_pull_rubrics import upload_demo_rubrics
from .push_pull_rubrics import upload_rubrics_from_file, download_rubrics_to_file

from plom import version_map_from_file, version_map_to_csv
from .version_map_utils import download_version_map
from .version_map_utils import save_version_map

from .scribble_utils import make_scribbles
from .scribble_hw_utils import make_hw_scribbles


# what you get from "from plom.create import *"
__all__ = [
    "clear_manager_login",
    "get_demo_classlist",
    "process_classlist_file",
    "upload_classlist",
    "upload_demo_classlist",
    "make_PDF",
    "make_scribbles",
    "make_hw_scribbles",
    "upload_rubrics",
    "download_rubrics",
    "upload_demo_rubrics",
    "upload_rubrics_from_file",
    "download_rubrics_to_file",
    "version_map_from_file",
    "version_map_to_csv",
    "download_version_map",
    "save_version_map",
    "status",
    "PlomClasslistValidator",
]
