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
    *** Warning: this script is "alpha" software at best! ***

    It inputs a .csv file from Canvas and outputs a new .csv file with
    the "return code (<int>)" column filled-in.  Any existing entries
    are checked to confirm correctness.

    This code is probably buggy and is certainly picky about the
    formatting of the csv file.  It may fail with cryptic errors.  You
    will want to have read "docs/returning_papers.md".  You should
    consider the output quite carefully both before uploading to
    Canvas and during the upload process.  Consider yourself warned...
    """)
    input('Press Enter to continue...')
    sns = canvas_csv_add_return_codes(canvas_fromfile, canvas_return_tofile)
    canvas_csv_check_pdf(sns)

    make_canvas_gradefile(canvas_fromfile, canvas_grades_tofile,
                          test_parthead=canvas_test_name)
