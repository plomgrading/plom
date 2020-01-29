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
    "3. Make sure the newserver is running and that the password for the 'scanner' user has been set."
)
print(
    '4. Run the "013_readQRCodes.py" script - this reads barcodes from the pages and files them away accordingly'
)
print(
    '5. Run the "014_sendPagesToServer.py" script to send identified pages to the server.'
)

print(
    '6. Pages that could not be identified are called "Unknowns". In that case run the "015_sendUnknownsToServer.py" script to send those unknowns to the server. The manager can then identify them manually.'
)

print(
    '7. If the system detects you trying to upload a test page corresponding to one already in the system (but not identical) then those pages are filed as "Collisions". If you have good paper-handling protocols then this should not happen. If you really do need to upload them to the system (the manager can look at them and decide) then run "016_sendCollisionsToServer.py" script.'
)
print(
    '8. If anything goes wrong and one of those scripts crash, you might need to clear the "scanner" login from the server. To do this run the "018_clearScannerLogin.py" script.'
)

print(
    '9. Run the "019_checkScanStatus.py" script to get a summary of scanning to date.'
)
