#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

"""
Read Canvas exported csv and remove test students etc, ensure all have Student Numbers.
"""

from pathlib import Path
from plom.finish.return_tools import import_canvas_csv


where_csv = Path(".")
canvas_in = where_csv / "Canvas_classlist_export.csv"
canvas_out = where_csv / "Canvas_classlist_01_cleaned.csv"

df = import_canvas_csv(canvas_in)

# TODO: assert all non-null "Student Number" column?

df.to_csv(canvas_out, index=False)
