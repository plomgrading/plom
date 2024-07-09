#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023-2024 Colin B. Macdonald

"""Put Plom's return codes into a Canvas sheet for use with `sending-conversations` script.

Reference: https://github.com/ubccapico/sending-conversations

Modify the `where_csv` variable if you're not running in the directory
with the CSV files.

You'll need the `return_codes.csv` file as created by
`plom-finish webpage --hex`.

There are other hardcoded values that will likely need to be changed.

TODO: could be modified so input doesn't need to be a Canvas sheet.
"""

from pathlib import Path

import pandas as pd

from plom.finish.return_tools import import_canvas_csv

where_csv = Path(".")
in_csv = where_csv / "canvas_latest_export.csv"
return_codes_csv = where_csv / "return_codes.csv"
out_csv = where_csv / "classlist_return_links.csv"

basename = "253t1"
baseurl = "https://amcweb.math.ubc.ca/~cbm/return20w1/" + basename
print('baseurl set to "{}"'.format(baseurl))
print("**  ^--- Double check this! ---^  **")

df_return_codes = pd.read_csv(return_codes_csv, dtype="object")

df = import_canvas_csv(in_csv)
# If you don't want to use the Plom function, do some cleaning something like:
# df = pd.read_csv(in_csv, dtype="object")
# df = df.drop([df.index[0], df.index[1]])
# df = df.reset_index(drop=True)

df = pd.merge(
    df, df_return_codes, how="left", left_on="Student Number", right_on="StudentID"
)


def f(x):
    """Apply this function to each row to define a new column."""
    if pd.isnull(x["Return Code"]):
        return x["Return Code"]
    sid = x["Student Number"]
    code = x["Return Code"]
    return "{}/{}_{}_{}.pdf".format(baseurl, basename, sid, code)


df["test_return_url"] = df.apply(f, axis=1)

df.to_csv(out_csv, index=False)
