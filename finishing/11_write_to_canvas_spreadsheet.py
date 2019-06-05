#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2018-2019 Colin B. Macdonald <cbm@m.fsf.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from return_tools import canvas_csv_add_return_codes, canvas_csv_check_pdf
from return_tools import make_canvas_gradefile

canvas_fromfile = 'canvas_from_export.csv'
canvas_return_tofile = 'canvas_return_codes_for_import.csv'
canvas_grades_tofile = 'canvas_grades_for_import.csv'

# TODO: should get this from project?!
canvas_test_name = 'Test2'  # almost certainly wrong

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
