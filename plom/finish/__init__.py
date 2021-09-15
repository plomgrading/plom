# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Plom tools related to post-grading finishing tasks."""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

from plom import __version__

CSVFilename = "marks.csv"

from .clearLogin import clear_manager_login

from .return_tools import canvas_csv_add_return_codes, canvas_csv_check_pdf
from .return_tools import make_canvas_gradefile
from .utils import rand_integer_code, salted_int_hash_from_str
from .utils import rand_hex, salted_hex_hash_from_str

# TODO: expose the contents from __main__ here

# TODO: what you get from "from plom.finish import *"
# __all__ = ["clear_manager_login"]
