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

# ----------------------


def buildDirectories():
    """Build the directories that this script needs"""
    # the list of directories. Might need updating.
    lst = ["sentPages", "sentPages/collisions"]
    for dir in lst:
        try:
            os.mkdir(dir)
        except FileExistsError:
            pass


def doFiling(rmsg, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        shutil.move(fname, "sentPages/collisions/{}".format(shortName))
        shutil.move(
            fname + ".qr", "sentPages/collisions/{}.qr".format(shortName),
        )
        shutil.move(
            fname + ".collide", "sentPages/collisions/{}.collide".format(shortName),
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(fname, "discardedPages/{}".format(shortName))
            shutil.move(fname + ".qr", "discardedPages/{}.qr".format(shortName))
            shutil.move(
                fname + ".collide", "discardedPages/{}.collide".format(shortName)
            )
        elif rmsg[1] == "original":
            print(rmsg[2])
            print("This should not happen - todo = log error in a sensible way")
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendCollidingFiles(fileList):
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


if __name__ == "__main__":
    # Look for pages in collisions
    fileList = glob("collidingPages/*.png")
    if warnUser(fileList) == False:
        quit()

    scanMessenger.startMessenger()

    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    scanMessenger.requestAndSaveToken("scanner", pwd)

    buildDirectories()

    sendCollidingFiles(fileList)
    scanMessenger.closeUser()
    scanMessenger.stopMessenger()
