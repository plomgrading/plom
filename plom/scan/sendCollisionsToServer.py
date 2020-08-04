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
from textwrap import dedent

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *
from plom import PlomImageExts
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
            "Uploading {} which collides with {}, tpv = {} {} {}".format(
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


def bundle_has_nonuploaded_collisions(bundle_dir):
    """Uploading a bundle sometimes results in collisions: does this one have any?

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        bool
    """
    if any((bundle_dir / "uploads/collidingPages").iterdir()):
        return True
    return False


def print_collision_warning(bundle_dir):
    """Print info about collisions and list of collisions in this bundle.

    Args:
        bundle_dir (str, Path): path to a bundle.
    """
    files = []
    for ext in PlomImageExts:
        files.extend((bundle_dir / "uploads/collidingPages").glob("*.{}".format(ext)))
    if not files:
        return
    print("\n>>>>>>>>>> WARNING <<<<<<<<<<")
    print("Detected the following {} colliding files:".format(len(files)))
    print("  {}".format("\n  ".join([x.name for x in files])))
    print("Before proceeding, we strongly recommend that you review these images in:")
    print("  {}".format(bundle_dir / "uploads/collidingPages"))

    print(
        dedent(
            """
            Uploading collisions will not cause an error but will require human
            intervention later using the Manager tool.  You should consider why this is
            happening: e.g., are you accidentally scanning papers twice?  Legitimate
            collisions can occur when re-scanning a folded or illegible page.
            """
        )
    )


def upload_collisions(bundleDir, server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    if password is None:
        pwd = getpass.getpass("Please enter the 'scanner' password: ")
    else:
        pwd = password

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
        for ext in PlomImageExts:
            files.extend(
                (bundleDir / "uploads/collidingPages").glob("*.{}".format(ext))
            )
        sendCollidingFiles(scanMessenger, bundleDir.name, files)
    finally:
        scanMessenger.closeUser()
        scanMessenger.stop()
