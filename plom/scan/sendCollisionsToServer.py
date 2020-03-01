#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
from glob import glob
import hashlib
import json
import os
import shutil

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *

# ----------------------


def doFiling(rmsg, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        for suf in ["", ".qr", ".collide"]:
            shutil.move(
                fname + suf, os.path.join("sentPages", "collisions", shortName + suf)
            )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            for suf in ["", ".qr", ".collide"]:
                shutil.move(
                    fname + suf, os.path.join("discardedPages", shortName + suf)
                )
        elif rmsg[1] == "original":
            print(rmsg[2])
            print("This should not happen - todo = log error in a sensible way")
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendCollidingFiles(scanMessenger, fileList):
    for fname in fileList:
        cname = fname + ".collide"
        with open(cname, "r") as fh:
            cdat = json.load(fh)
        print(
            "File {} collides with {} - has tpv = {} {} {}".format(
                fname, cdat[0], cdat[1], cdat[2], cdat[3]
            )
        )
        ts = str(cdat[1]).zfill(4)
        ps = str(cdat[2]).zfill(2)
        vs = str(cdat[3])
        code = "t{}p{}v{}".format(ts, ps, vs)
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        shortName = os.path.split(fname)[1]
        rmsg = scanMessenger.uploadCollidingPage(
            code, int(ts), int(ps), int(vs), shortName, fname, md5
        )
        doFiling(rmsg, shortName, fname)


def warnUser(fileList):
    if len(fileList) == 0:
        print("No colliding pages. Nothing to do.")
        return False

    print(">>>>>>>>>> WARNING <<<<<<<<<<")
    print("In most use cases you should have no colliding pages.")
    print("Detected the following colliding files:\n\t", fileList)
    print(
        'We strongly recommend that you review the images in the "collidingPages" directory before proceeding.'
    )
    yn = input("********** Are you sure you want to proceed [y/N] **********  ")
    if yn == "y":
        print("Proceeding.")
        return True
    else:
        print("Terminating.")
        return False


def uploadCollisions(server=None, password=None):
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
            "In order to force-logout the existing authorisation run the 018_clearScannerLogin.py script."
        )
        exit(0)

    fileList = glob("collidingPages/*.png")
    if warnUser(fileList) == False:
        exit(0)

    sendCollidingFiles(scanMessenger, fileList)
    scanMessenger.closeUser()
    scanMessenger.stop()
