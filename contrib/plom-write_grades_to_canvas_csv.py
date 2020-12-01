#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Read in a Canvas-exported spreadsheet and prepare marks for upload.

This will create a new csv file that you can manually upload/import
back to Canvas.
"""

__copyright__ = "Copyright (C) 2019-2020 Colin B. Macdonald and others"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"

import argparse

from plom.finish import make_canvas_gradefile

canvas_fromfile = "canvas_latest_export.csv"
canvas_grades_tofile = "canvas_grades_for_import.csv"
# TODO: check if former exists and latter does not, and give some
# basic instructions

# TODO: should get this from project?!
Default_canvas_test_name = "Midterm ("  # almost certainly wrong


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-p",
        type=str,
        metavar="PART_COLUMN_NAME",
        help='Partial Canvas column name of test, as detailed as possible (defaults to "{}", see docs)'.format(
            Default_canvas_test_name
        ),
    )

    args = parser.parse_args()

    if not args.p:
        canvas_test_name = Default_canvas_test_name
    else:
        canvas_test_name = args.p

    print(
        """
    *** Warning: this script is "pre-alpha" software ***

    This scripts reads in `marks.csv` created by `plom-finish`.

    This script then looks for "{}",
    which you should have exported from Canvas.
    This file must have an existing column which will be filled with
    to.  Canvas columns have names like "XXXX (<number>)".
    This script is going to try to complete the column name from
    "{}"

    It outputs a new .csv file for importing back into Canvas:
    "{}"

    Read "docs/returning_papers.md" before using this.
    """.format(
            canvas_fromfile, canvas_test_name, canvas_grades_tofile
        )
    )
    input("Press Enter to continue...")

    print()
    make_canvas_gradefile(
        canvas_fromfile, canvas_grades_tofile, test_parthead=canvas_test_name
    )
