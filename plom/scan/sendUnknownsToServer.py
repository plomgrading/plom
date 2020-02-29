#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
from glob import glob
import hashlib
import os
import shutil

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *


def doFiling(rmsg, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        print("{} uploaded as unknown page.".format(fname))
        shutil.move(fname, os.path.join("sentPages", "unknowns", shortName))
        shutil.move(
            fname + ".qr", os.path.join("sentPages", "unknowns", shortName + "qr")
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(fname, os.path.join("discardedPages", shortName))
            shutil.move(
                fname + ".qr", os.path.join("discardedPages", shortName + ".qr")
            )
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendUnknownFiles(scanMessenger, fileList):
    for fname in fileList:
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        shortName = os.path.split(fname)[1]
        rmsg = scanMessenger.uploadUnknownPage(shortName, fname, md5)
        doFiling(rmsg, shortName, fname)


def uploadUnknowns(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(args.server)
    scanMessenger.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        scanMessenger.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 018_clearScannerLogin.py script."
        )
        exit(0)

    # Look for pages in unknowns
    fileList = glob("unknownPages/*.png")
    sendUnknownFiles(scanMessenger, fileList)
    scanMessenger.closeUser()
    scanMessenger.stop()
