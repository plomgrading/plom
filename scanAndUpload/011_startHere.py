#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os


def buildDirectories():
    """Build the directories that this scripts needs"""
    # the list of directories. Might need updating.
    lst = [
        "archivedPDFs",
        "scannedExams",
    ]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


buildDirectories()

print("To start the scan process")
print(
    "0. Copy your PDF scans of the tests into the directory scannedExams. This script has created that directory if it did not already exist."
)
print("1. Edit the server.toml file with the relevant server data.")
print(
    '2. Run the "012_scansToImages.py" script - this processes your PDFs into individual pages'
)
print(
    '3. Run the "013_readQRCodes.py" script - this reads barcodes from the pages and files them away accordingly'
)
print(
    "4. Make sure the newserver is running and that the password for the 'scanner' user has been set."
)
print('5. Run the "014_sendPagesToServer.py" script')
