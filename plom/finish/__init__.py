# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2024 Colin B. Macdonald

"""Plom tools related to post-grading finishing tasks."""

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from plom import __version__
from .utils import rand_integer_code, salted_int_hash_from_str
from .utils import rand_hex, salted_hex_hash_from_str


CSVFilename = "marks.csv"
RubricListFilename = "rubric_list.json"
TestRubricMatrixFilename = "test_rubric_matrix.json"

from .start_messenger import start_messenger
from .start_messenger import with_finish_messenger
from .clear_manager_login import clear_manager_login

from .spreadsheet import pull_spreadsheet
from .reassemble_completed import reassemble_paper, reassemble_all_papers
from .assemble_solutions import assemble_solutions
from .rubric_downloads import download_rubric_files
from .coded_return import make_coded_return_webpage
from .audit import audit

from .return_tools import canvas_csv_add_return_codes, canvas_csv_check_pdf
from .return_tools import make_canvas_gradefile


# TODO: expose the contents from __main__ here
# what you get from "from plom.finish import *"
__all__ = [
    "clear_manager_login",
    "pull_spreadsheet",
    "reassemble_paper",
    "reassemble_all_papers",
    "assemble_solutions",
    "download_rubric_files",
    "make_coded_return_webpage",
]
