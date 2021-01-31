# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

"""
Rename files for online distribution.

1. Make the files in Plom first
2. Run the 01 script to make randomized filenames
3. Run this.
"""

from pathlib import Path
import shutil
import pandas as pd

where_csv = Path(".")
in_csv = where_csv / "random_codes.csv"
where_pdf = Path("papersToPrint")
dist_pdf = Path("distribute")


def do_renaming(r):
    """Rename files based on info from each row of the spreadsheet."""
    if pd.isnull(r["sID"]):
        f = where_pdf / "exam_{:04d}.pdf".format(int(r["test_number"]))
    else:
        f = where_pdf / "exam_{:04d}_{}.pdf".format(int(r["test_number"]), r["sID"])
    out = dist_pdf / r["test_filename"]
    print("{} -> {}".format(f, out))
    shutil.copy2(f, out)


dist_pdf.mkdir(exist_ok=True)

df = pd.read_csv(in_csv, dtype="object")

df.apply(lambda row: do_renaming(row), axis=1)

