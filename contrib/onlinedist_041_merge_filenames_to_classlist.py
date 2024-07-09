#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald

"""Merge the filenames in the Canvas classlist.

TODO: probably the 04x scripts can all be merged into one calling
some functions.

New columns:
    "test_filename"
    "test_hex"
    "test_id"
"""

from pathlib import Path
import pandas as pd


where_csv = Path(".")
canvas_csv = where_csv / "Canvas_classlist_02_with_rooms_edited.csv"
codes_csv = where_csv / "random_codes.csv"
out_csv = where_csv / "Canvas_classlist_041_filenames.csv"

df = pd.read_csv(canvas_csv, dtype="object")
codes = pd.read_csv(codes_csv, dtype="object")

# Merge the "test_filename" and "test_hex" columns
codes = codes.dropna()
d = dict(zip(codes["sID"], codes["test_hex"]))
df["test_hex"] = df["Student Number"].map(d)
d = dict(zip(codes["sID"], codes["test_filename"]))
df["test_filename"] = df["Student Number"].map(d)
d = dict(zip(codes["sID"], codes["test_number"]))
df["test_number"] = df["Student Number"].map(d)
# df = pd.merge(df, codes[["sID", "test_filename", "test_hex"]], left_on="Student Number", right_on="sID", how='left')


# Yes you really want to check: I caught an off-by-one error in my spreadsheet
def assert_it_worked(row):
    if pd.isnull(row["test_filename"]):
        print("problem row:")
        print(row)
        raise ValueError("Expect non-null entry was not!  Missing student somewhere?")


df.apply(assert_it_worked, axis=1)

df.to_csv(out_csv, index=False)
