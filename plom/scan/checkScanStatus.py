#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass

from plom.misc_utils import format_int_list_with_runs
from plom.messenger import ScanMessenger
from plom.plom_exceptions import *


def checkStatus(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    # get started
    try:
        scanMessenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    spec = scanMessenger.get_spec()

    ST = (
        scanMessenger.getScannedTests()
    )  # returns pairs of [page,version] - only display pages
    UT = scanMessenger.getUnusedTests()
    IT = scanMessenger.getIncompleteTests()
    scanMessenger.closeUser()
    scanMessenger.stop()

    print("Test papers unused: [{}]".format(format_int_list_with_runs(UT)))

    print("Scanned tests in the system:")
    for t in ST:
        scannedTPages = []
        scannedHWPages = []
        for x in ST[t]:
            if x[0][0] == "t":  # is a test page = "t.p"
                p = int(x[0].split(".")[1])
                scannedTPages.append(p)
            elif x[0][0] == "h":  # is a hw page = "h.q.o"
                q = int(x[0].split(".")[1])
                if q not in scannedHWPages:
                    scannedHWPages.append(q)

        print(
            "\t{}: testPages [{}] hwPages [{}]".format(
                t,
                format_int_list_with_runs(scannedTPages),
                format_int_list_with_runs(scannedHWPages),
            )
        )

    print("Incomplete scans - listed with their missing pages: ")
    for t in IT:
        missingPagesT = []
        missingPagesH = []
        for x in IT[t]:  # each entry is [page, version, scanned?]
            if x[0][0] == "t":  # is a test page
                p = int(x[0].split(".")[1])
                if x[2] is False:
                    missingPagesT.append(p)
            elif x[0][0] == "h":  # is a w page
                q = int(x[0].split(".")[1])
                if x[2] is False:
                    missingPagesH.append(q)
        print(
            "\t{}: t[{}] h[{}]".format(
                t,
                format_int_list_with_runs(missingPagesT),
                format_int_list_with_runs(missingPagesH),
            )
        )


def checkMissingHWQ(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    # get started
    try:
        scanMessenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    missingHWQ = scanMessenger.getMissingHW()
    scanMessenger.closeUser()
    scanMessenger.stop()

    return missingHWQ


def replaceMissingHWQ(server, password, student_id, question):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    # get started
    try:
        scanMessenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    rval = scanMessenger.replaceMissingHWQuestion(
        student_id=student_id, test=None, question=question
    )  # can replace by SID or by test-number
    scanMessenger.triggerUpdateAfterHWUpload()

    scanMessenger.closeUser()
    scanMessenger.stop()

    return rval
