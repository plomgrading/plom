#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald

"""Rename files for online distribution.

1. Make the files in Plom first
2. Run the 01 script to make randomized filenames
3. Run this.
"""

from pathlib import Path
import shutil
import pandas as pd

where_csv = Path(".")
# unfort need room info too: if you don't need multiple rooms, this would
# and is much easier:
# in_csv = where_csv / "random_codes.csv"
in_csv = where_csv / "Canvas_classlist_043_ready.csv"
where_pdf = Path("papersToPrint")
dist_pdf = Path("distribute")

# sid = "sID"  # if using random-codes.csv
sid = "Student Number"


def do_renaming_simple(r):
    """Rename files based on info from each row of the spreadsheet."""
    if pd.isnull(r[sid]):
        f = where_pdf / "exam_{:04d}.pdf".format(int(r["test_number"]))
    else:
        f = where_pdf / "exam_{:04d}_{}.pdf".format(int(r["test_number"]), r[sid])
    out = dist_pdf / r["test_filename"]
    print("{} -> {}".format(f, out))
    shutil.copy2(f, out)


def do_renaming(r):
    """Rename files based on info from each row of the spreadsheet."""
    if pd.isnull(r[sid]):
        f = "exam_{:04d}.pdf".format(int(r["test_number"]))
        room = "spare"
    else:
        f = "exam_{:04d}_{}.pdf".format(int(r["test_number"]), r[sid])
        room = r["test_room"]
    out = dist_pdf / room / r["test_filename"]
    print("{} -> {}".format(f, out))
    shutil.copy2(where_pdf / f, out)


df = pd.read_csv(in_csv, dtype="object")

subdirs = list(df["test_room"].unique())
subdirs.append("spare")

print("creating dir: {}".format(dist_pdf))
dist_pdf.mkdir(exist_ok=True)
for x in subdirs:
    print("creating dir: {}".format(dist_pdf / x))
    (dist_pdf / x).mkdir(exist_ok=True)

df.apply(lambda row: do_renaming(row), axis=1)

html = r"""<html>
<body>
<p>Nothing to see here</p>
<!-- You may want to configure your webserver to ensure there is more than
     this file stopping folks from getting a directory listing! -->
</body>
</html>
"""

subdirs.append(".")
for x in subdirs:
    with open(dist_pdf / x / "index.html", "w") as f:
        f.write(html)
