# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import hashlib
import shutil
from pathlib import Path

from plom.messenger import ScanMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom import PlomImageExts
from plom.scan.sendPagesToServer import extract_order


def doFiling(rmsg, bundle, f):
    if rmsg[0]:  # msg should be [True, "success", success message]
        print("{} uploaded as unknown page.".format(f))
        shutil.move(f, bundle / "uploads/sentPages/unknowns" / f.name)
        shutil.move(
            Path(str(f) + ".qr"),
            bundle / "uploads/sentPages/unknowns" / f"{f.name}.qr",
        )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            shutil.move(f, bundle / "uploads/discardedPages" / f.name)
            shutil.move(
                Path(str(f) + ".qr"),
                bundle / "uploads/discardedPages" / f"{f.name}.qr",
            )
        else:
            print(rmsg[2])
            print("This should not happen - todo = log error in sensible way")


def sendUnknownFiles(msgr, bundle_name, files):
    for fname in files:
        md5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        order = extract_order(fname)
        bundle_order = order
        rmsg = msgr.uploadUnknownPage(fname, order, md5, bundle_name, bundle_order)
        doFiling(rmsg, Path("bundles") / bundle_name, fname)


def bundle_has_nonuploaded_unknowns(bundle_dir):
    """Does this bundle have unknown pages that are not uploaded.

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        bool
    """
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

    try:
        scanMessenger.requestAndSaveToken("scanner", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-scan clear"'
        )
        raise

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
