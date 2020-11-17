#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import os
import shutil
from pathlib import Path

import getpass

from plom.messenger import ScanMessenger
from plom.plom_exceptions import *
from plom import PlomImageExts


def doFiling(rmsg, bundle, shortName, fname):
    if rmsg[0]:  # msg should be [True, "success", success message]
        # print(rmsg[2])
        print("{} uploaded as unknown page.".format(fname))
        shutil.move(fname, bundle / Path("uploads/sentPages/unknowns") / shortName)
        shutil.move(
            Path(str(fname) + ".qr"),
            bundle / Path("uploads/sentPages/unknowns") / (str(shortName) + ".qr"),
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(fname, bundle / Path("uploads/discardedPages") / shortName)
            shutil.move(
                Path(str(fname) + ".qr"),
                bundle / Path("uploads/discardedPages") / (str(shortName) + ".qr"),
            )
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def extractOrder(fname):
    """filename is of the form blah-n.png, extract the 'n' and return it as an integer"""
    npng = fname.split("-")[-1]
    n = npng.split(".")[0]
    return int(n)


def sendUnknownFiles(msgr, bundle_name, files):
    for fname in files:
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        shortName = os.path.split(fname)[1]
        order = extractOrder(shortName)
        bundle_order = order
        rmsg = msgr.uploadUnknownPage(
            shortName, fname, order, md5, bundle_name, bundle_order
        )
        doFiling(rmsg, Path("bundles") / bundle_name, shortName, fname)


def bundle_has_nonuploaded_unknowns(bundle_dir):
    """Does this bundle have unknown pages that are not uploaded.

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        bool
    """
    files = []
    if any((bundle_dir / "unknownPages").iterdir()):
        return True
    return False


def print_unknowns_warning(bundle_dir):
    """Print info about unknowns and list of unknowns in this bundle.

    Args:
        bundle_dir (str, Path): path to a bundle.
    """
    files = []
    for ext in PlomImageExts:
        files.extend((bundle_dir / "unknownPages").glob("*.{}".format(ext)))
    if not files:
        return
    print("\n>>>>>>>>>> NOTE <<<<<<<<<<")
    print("Processing resulted in these {} unknown files:".format(len(files)))
    print("  {}".format("\n  ".join([x.name for x in files])))
    # TODO: this is XX out of YY pages in the bundle
    print("UnknownPages can result from poor-quality scans or damaged pages where")
    print("QR codes cannot be read properly.  They also result from any scanned pages")
    print("without QR codes, such as any Extra Pages.  Uploading small numbers of")
    print("unknown pages is common but will require human intervention later with the")
    print("Manager tool.  If the number of such pages seems high, you may want to")
    print("look in {}\n".format(bundle_dir / "unknownPages"))


def upload_unknowns(bundle_dir, server=None, password=None):
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
        if not bundle_dir.is_dir():
            raise ValueError("should've been a directory!")
        files = []
        # Look for pages in unknowns
        for ext in PlomImageExts:
            files.extend((bundle_dir / "unknownPages").glob("*.{}".format(ext)))
        sendUnknownFiles(scanMessenger, bundle_dir.name, files)
    finally:
        scanMessenger.closeUser()
        scanMessenger.stop()
