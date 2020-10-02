#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Read in a Canvas-exported spreadsheet and prepare data for upload.

This will create two csv files:

  1. `canvas_return_codes_to_import.csv`.
  2. `canvas_grades_to_import.csv`.

You can upload/import one or both of these files back to Canvas.  If
you kept the same salt, you may be able to upload just the grades.

TODO: testname etc not ideal
"""

__copyright__ = "Copyright (C) 2019-2020 Colin B. Macdonald and others"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"

import argparse

from .return_tools import canvas_csv_add_return_codes, canvas_csv_check_pdf
from .return_tools import make_canvas_gradefile

canvas_fromfile = "canvas_from_export.csv"
canvas_return_tofile = "canvas_return_codes_for_import.csv"
canvas_grades_tofile = "canvas_grades_for_import.csv"

# TODO: should get this from project?!
Default_canvas_test_name = "Midterm ("  # almost certainly wrong

# TODO: check if former exists and latter does not, and give some
# basic instructions


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(description="Make csv file for upload to Canvas.")
    parser.add_argument(
        "--saltstr", type=str, help="Per-course secret salt string (see docs)"
    )
    parser.add_argument(
        "--findcol",
        type=str,
        help='Partial Canvas column name, as detailed as possible (defaults to "{}", see docs)'.format(
            Default_canvas_test_name
        ),
    )

    args = parser.parse_args()
    if not args.saltstr:
        print("TODO: how can we should help here instead?")
        raise ValueError("You must set the Salt String")
    saltstr = args.saltstr
    print('Salt is "{0}"'.format(saltstr))

    if not args.findcol:
        canvas_test_name = Default_canvas_test_name
    else:
        canvas_test_name = args.findcol

    print(
        """
    *** Warning: this script is "pre-alpha" software ***

    You basically shouldn't be running it at all.

    This script looks for "{0}", which you should
    have exported from Canvas.  It outputs two new .csv files for
    importing back into canvas.

      * "{1}":
        The "return code" column will be filled.  Any existing
        return codes will be checked to confirm correctness.

      * "{2}":
        The "{3}" column will be filled with the results of this
        test.  EDIT THIS SCRIPT TO USE A DIFFERENT COLUMN.

    Read "docs/returning_papers.md" before using this.
    """.format(
            canvas_fromfile,
            canvas_return_tofile,
            canvas_grades_tofile,
            canvas_test_name,
        )
    )
    input("Press Enter to continue...")

    print()
    sns = canvas_csv_add_return_codes(
        canvas_fromfile, canvas_return_tofile, saltstr=saltstr
    )

    print()
    canvas_csv_check_pdf(sns)

    print()
    make_canvas_gradefile(
        canvas_fromfile, canvas_grades_tofile, test_parthead=canvas_test_name
    )
