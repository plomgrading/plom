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
import json
import os
import shutil
import scanMessenger


def buildDirectories():
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["sentPages", "sentPages/unknowns"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


def doFiling(rmsg, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
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


def sendUnknownFiles(fileList):
    for fname in fileList:
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        shortName = os.path.split(fname)[1]
        rmsg = scanMessenger.uploadUnknownPage(shortName, fname, md5)
        doFiling(rmsg, shortName, fname)


if __name__ == "__main__":
    scanMessenger.startMessenger()

    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    scanMessenger.requestAndSaveToken("scanner", pwd)

    buildDirectories()

    # Look for pages in unknowns
    fileList = glob("unknownPages/*.png")
    print(fileList)
    sendUnknownFiles(fileList)
    scanMessenger.closeUser()
    scanMessenger.stopMessenger()
