#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald

"""Write the URLs for each student to get their test from.

Read columns:
    "test_filename"
    "test_room": the machine readable room name.

New columns:
    "test_url": a personalized URL
"""

from pathlib import Path
import urllib
import pandas as pd

where_csv = Path(".")
canvas_csv = where_csv / "Canvas_classlist_041_filenames.csv"
out_csv = where_csv / "Canvas_classlist_042_urls.csv"

df = pd.read_csv(canvas_csv, dtype="object")

baseurl = "https://amcweb.math.ubc.ca/~cbm/bmeg220/"


def make_url(r):
    """Make a filename from a row of the spreadsheet."""
    if pd.isnull(r["Student Number"]):
        print("problem row: {}".format(r))
        raise ValueError("Strip non-students without Student Numbers first.")
    # Used to extract from human-readble but should be clean: doesn't hurt
    urlroom = r["test_room"].replace(" ", "")
    urlroom = urlroom.lower()
    urlroom = urllib.parse.quote_plus(urlroom)
    return baseurl + urlroom + "/" + r["test_filename"]


df["test_url"] = df.apply(lambda row: make_url(row), axis=1)

df.to_csv(out_csv, index=False)
