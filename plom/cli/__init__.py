# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2023, 2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2025 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Bryan Tanady


"""Scriptable Plom tools for use by experts."""

__copyright__ = "Copyright (C) 2018-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom.common import __version__

from .start_messenger import with_messenger, start_messenger, clear_login
from .list_bundles import list_bundles
from .bundle_tools import upload_bundle, bundle_map_page
from .identify_tools import id_paper, un_id_paper
from .finish_tools import get_reassembled, get_unmarked, get_marks_as_csv_string
from .source_tools import upload_source
from .source_tools import delete_source
from .spec_tools import upload_spec
from .task_tools import reset_task
from .classlist_tools import delete_classlist
from .classlist_tools import download_classlist
from .classlist_tools import upload_classlist
from .rectangle_extractor_tools import extract_rectangle

# what you get from "from plom.cli import *"
__all__ = [
    "bundle_map_page",
    "id_paper",
    "un_id_paper",
    "list_bundles",
    "upload_bundle",
    "get_reassembled",
    "delete_source",
    "upload_source",
    "upload_spec",
    "reset_task",
    "delete_classlist",
    "download_classlist",
    "upload_classlist",
    "extract_rectangle",
]
