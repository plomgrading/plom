#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
import hashlib
import json
import os
import shutil
from pathlib import Path

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *
from plom import PlomImageExtWhitelist
from .sendUnknownsToServer import extractOrder


def doFiling(rmsg, bundle, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        for suf in ["", ".qr", ".collide"]:
            shutil.move(
                Path(str(fname) + suf),
                bundle / Path("uploads/sentPages/collisions") / Path(shortName + suf),
            )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            for suf in ["", ".qr", ".collide"]:
                shutil.move(
                    Path(str(fname) + suf),
                    bundle / Path("uploads/discardedPages") / Path(shortName + suf),
                )
        elif rmsg[1] == "original":
            print(rmsg[2])
            print("This should not happen - todo = log error in a sensible way")
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendCollidingFiles(scanMessenger, bundle_name, fileList):
    for fname in fileList:
        with open(Path(str(fname) + ".collide"), "r") as fh:
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
        bundle_order = extractOrder(shortName)
        rmsg = scanMessenger.uploadCollidingPage(
            code,
            int(ts),
            int(ps),
            int(vs),
            shortName,
            fname,
            md5,
            bundle_name,
            bundle_order,
        )
        doFiling(rmsg, Path("bundles") / bundle_name, shortName, fname)


def warnAndAskUser(fileList, bundle_dir):
    """Confirm collisions by asking user.

    Returns False if we should stop (user says no).  Returns True if
    there were no colliding pages or if user says yes.
    """
    if len(fileList) == 0:
        print("No colliding pages. Nothing to do.")
        return True

    print(">>>>>>>>>> WARNING <<<<<<<<<<")
    print("In most use cases you should have no colliding pages.")
    print("Detected the following colliding files:\n\t", fileList)
    print("Before proceeding, We strongly recommend that you review the images in:")
    print("  {}".format(bundle_dir / "uploads/collidingPages"))
    yn = input("********** Are you sure you want to proceed [y/N] **********  ")
    if yn == "y":
        print("Proceeding.")
        return True
    else:
        print("Terminating.")
        return False


def uploadCollisions(bundleDir, server=None, password=None):
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

    try:
        if not bundleDir.is_dir():
            raise ValueError("should've been a directory!")

        files = []
        for ext in PlomImageExtWhitelist:
            files.extend(
                (bundleDir / "uploads/collidingPages").glob("*.{}".format(ext))
            )
        if warnAndAskUser(files, bundleDir) == False:
            exit(2)
        sendCollidingFiles(scanMessenger, bundleDir.name, files)
    finally:
        scanMessenger.closeUser()
        scanMessenger.stop()
