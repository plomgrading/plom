# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald
# Copyright (C) 2021 Jenny Li

"""
Read Plom's produced_papers.csv and make new spreadsheet of random codes for online distro.

1. Use `plom-build` to create your `produced_papers.csv`.
2. Run this.
3. Output file `random_codes.csv` has two new columns:
    - test_hex: a random hex string (from a good urandom num gen)
    - test_filename: a filename with the random hex in it, appropriate for
      distributions.
4. This doesn't actually rename any pdf files: run 02_rename_for_distro.py
   for that.

Note: the "stem" of the filename is hardcoded below as `name`: you will
need to change that!
"""

from pathlib import Path
import os
import binascii
import pandas as pd

where_csv = Path(".")
in_csv = where_csv / "produced_papers.csv"
out_csv = where_csv / "random_codes.csv"

df = pd.read_csv(in_csv, dtype="object")


# *** IMPORTANT TO CHANGE
name = "quiz1"
# TODO take from spec instead?

NN = 6  # 12 hex digits


# todo: does plom already have this function somewhere?
def random_hex():
    return binascii.b2a_hex(os.urandom(NN)).decode()


def make_file_name(r):
    """Make a filename from a row of the spreadsheet."""
    if pd.isnull(r["sID"]):
        # return r['sID']  # i.e., NaN
        return "{}_{:04d}_{}.pdf".format(name, int(r["test_number"]), r["test_hex"])
    return "{}_{:04d}_{}_{}.pdf".format(
        name, int(r["test_number"]), r["sID"], r["test_hex"]
    )


df["test_hex"] = df.apply(lambda row: random_hex(), axis=1)
df["test_filename"] = df.apply(lambda row: make_file_name(row), axis=1)

df.to_csv(out_csv, index=False)

# TODO: optionally merge these columns into the Canvas spreadsheet too?
