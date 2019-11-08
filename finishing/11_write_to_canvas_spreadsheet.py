#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Read in a Canvas-exported spreadsheet and prepare data for upload.

This will create two csv files:

  1. `canvas_return_codes_to_import.csv`.
  2. `canvas_grades_to_import.csv`.

You can upload/import one or both of these files back to Canvas.  If
you kept the same salt, you may be able to upload just the grades.

TODO: testname etc not ideal
"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Colin B. Macdonald"
__credits__ = ["Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from return_tools import canvas_csv_add_return_codes, canvas_csv_check_pdf
from return_tools import make_canvas_gradefile

canvas_fromfile = 'canvas_from_export.csv'
canvas_return_tofile = 'canvas_return_codes_for_import.csv'
canvas_grades_tofile = 'canvas_grades_for_import.csv'

# TODO: should get this from project?!
canvas_test_name = 'Midterm ('  # almost certainly wrong

# TODO: check if former exists and latter does not, and give some
# basic instructions


if __name__ == '__main__':
    print("""
    *** Warning: this script is "alpha" software ***

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
    """.format(canvas_fromfile, canvas_return_tofile, canvas_grades_tofile,
               canvas_test_name))
    input('Press Enter to continue...')

    print()
    sns = canvas_csv_add_return_codes(canvas_fromfile, canvas_return_tofile)

    print()
    canvas_csv_check_pdf(sns)

    print()
    make_canvas_gradefile(canvas_fromfile, canvas_grades_tofile,
                          test_parthead=canvas_test_name)
