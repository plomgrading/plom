#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
from misc_utils import format_int_list_with_runs
import scanMessenger


if __name__ == "__main__":
    scanMessenger.startMessenger()

    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    scanMessenger.requestAndSaveToken("scanner", pwd)
    spec = scanMessenger.getInfoGeneral()

    ST = (
        scanMessenger.getScannedTests()
    )  # returns pairs of [page,version] - only display pages
    UT = scanMessenger.getUnusedTests()
    IT = scanMessenger.getIncompleteTests()
    scanMessenger.closeUser()
    scanMessenger.stopMessenger()

    print("Test papers unused: [{}]".format(format_int_list_with_runs(UT)))

    print("Scanned tests in the system:")
    for t in ST:
        scannedPages = [x[0] for x in ST[t]]
        print("\t{}: [{}]".format(t, format_int_list_with_runs(scannedPages)))

    print("Incomplete scans - listed with their missing pages: ")
    for t in IT:
        missingPages = [x[0] for x in IT[t]]
        print("\t{}: [{}]".format(t, format_int_list_with_runs(missingPages)))
