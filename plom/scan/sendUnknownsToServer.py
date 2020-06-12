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
from plom import PlomImageExtWhitelist


def doFiling(rmsg, shortName, fname):
    # current directory is "bundle", but we need to put files in "../upload/blah"
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        print("{} uploaded as unknown page.".format(fname))
        shutil.move(
            fname, os.path.join("..", "uploads", "sentPages", "unknowns", shortName)
        )
        shutil.move(
            fname + ".qr",
            os.path.join("..", "uploads", "sentPages", "unknowns", shortName + "qr"),
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(
                fname, os.path.join("..", "uploads", "discardedPages", shortName)
            )
            shutil.move(
                fname + ".qr",
                os.path.join("..", "uploads", "discardedPages", shortName + ".qr"),
            )
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def extractOrder(fname):
    """filename is of the form blah-n.png, extract the 'n' and return it as an integer
    """
    npng = fname.split("-")[-1]
    n = npng.split(".")[0]
    return int(n)


def sendUnknownFiles(scanMessenger, fileDict):
    for bundle in fileDict:
        for fname in fileDict[bundle]:
            md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
            shortName = os.path.split(fname)[1]
            order = extractOrder(shortName)
            rmsg = scanMessenger.uploadUnknownPage(shortName, fname, order, md5, bundle)
            doFiling(rmsg, shortName, fname)


def uploadUnknowns(server=None, password=None):
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
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        exit(10)

    fileDict = {}  # list of files by bundle

    # go into bundles directory
    os.chdir("bundles")
    for bundleDir in os.scandir():
        # make sure is directory
        if not bundleDir.is_dir():
            continue
        fileDict[bundleDir.name] = []
        # Look for pages in unknowns
        for ext in PlomImageExtWhitelist:
            fileDict[bundleDir.name].extend(
                glob(os.path.join(bundleDir, "unknownPages", "*.{}".format(ext)))
            )
    sendUnknownFiles(scanMessenger, fileDict)
    scanMessenger.closeUser()
    scanMessenger.stop()
