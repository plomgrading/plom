#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

print("To start the scan process")
print(
    "0. Wait until most of the marking and identifying is done before running any finishing scripts - otherwise you won't acheive much running things the scripts in this directory."
)
print('1. Run the "022_check completed.py" script.')
print(
    '2. When you are satisfied with the amount of progress, run the "023_check completed.py" script, to produce a spreadsheet of completed papers and their marks.'
)
print(
    '3. Run the "024_reassemble.py" script to start building PDFs of processed papers.'
)
