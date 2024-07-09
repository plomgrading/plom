#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald

"""Rename files for online distribution: just the spares.

This was original written to do all the files but if there are multiple
room than we needed more work.

1. Make the files in Plom first
2. Run the 01/02 script to make randomized filenames
3. Run this.
"""

from pathlib import Path
import shutil
import pandas as pd

where_csv = Path(".")
in_csv = where_csv / "random_codes.csv"
where_pdf = Path("papersToPrint")
dist_pdf = Path("distribute")


def rename_and_move_spares(r):
    """Rename files based on info from each row of the spreadsheet."""
    if not pd.isnull(r["sID"]):
        return
    f = where_pdf / "exam_{:04d}.pdf".format(int(r["test_number"]))
    out = dist_pdf / "spare" / r["test_filename"]
    print("{} -> {}".format(f, out))
    shutil.copy2(f, out)


df = pd.read_csv(in_csv, dtype="object")

df.apply(rename_and_move_spares, axis=1)
