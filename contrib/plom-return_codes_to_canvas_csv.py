#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Read in a Canvas-exported spreadsheet and add return codes.

`plom-finish` can create a webpage which students can access
via their Student ID and a private secret code.  This script
prepares a csv file for Canvas import containing the secret codes.
"""

__copyright__ = "Copyright (C) 2019-2020 Colin B. Macdonald and others"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"

import argparse

from plom.finish import canvas_csv_add_return_codes, canvas_csv_check_pdf

canvas_fromfile = "canvas_from_export.csv"
canvas_return_tofile = "canvas_return_codes_for_import.csv"
# TODO: check if former exists and latter does not, and give some
# basic instructions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salt",
        type=str,
        required=True,
        help="Per-course secret salt string (required). See docs for details.",
    )

    args = parser.parse_args()
    saltstr = args.salt
    print('Salt is "{0}"'.format(saltstr))
    print(
        """
    *** Warning: this script is "pre-alpha" software ***

    This script looks for "{0}", which you should
    have exported from Canvas.  It outputs a new .csv files for
    importing back into canvas:

      * "{1}":
        The "return code" column will be filled.  Any existing
        return codes will be checked to confirm correctness.

    Read "docs/returning_papers.md" before using this.
    """.format(
            canvas_fromfile, canvas_return_tofile
        )
    )
    input("Press Enter to continue...")

    print()
    sns = canvas_csv_add_return_codes(
        canvas_fromfile, canvas_return_tofile, saltstr=saltstr
    )

    print()
    canvas_csv_check_pdf(sns)
