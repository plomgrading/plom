#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import getpass
from misc_utils import format_int_list_with_runs
import scanMessenger
from plom_exceptions import *


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(
        description="Run the QR-code reading script. No arguments = run as normal."
    )
    parser.add_argument("-w", "--password", type=str)
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help="Which server to contact.",
    )
    args = parser.parse_args()
    if args.server and ":" in args.server:
        s, p = args.server.split(":")
        scanMessenger.startMessenger(s, port=p)
    else:
        scanMessenger.startMessenger(args.server)

    # get the password if not specified
    if args.password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = args.password

    # get started
    try:
        scanMessenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 018_clearScannerLogin.py script."
        )
        exit(0)

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
