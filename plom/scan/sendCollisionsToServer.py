# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import hashlib
import json
from pathlib import Path
import shutil
from textwrap import dedent

from plom.messenger import ScanMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom import PlomImageExts
from plom.scan.sendPagesToServer import extract_order


def doFiling(rmsg, bundle, f):
    if rmsg[0]:  # msg should be [True, "success", success message]
        for suf in ["", ".qr", ".collide"]:
            shutil.move(
                Path(str(f) + suf),
                bundle / "uploads/sentPages/collisions" / (f.name + suf),
            )
    else:  # msg = [False, reason, message]
        if rmsg[1] == "duplicate":
            print(rmsg[2])
            for suf in ["", ".qr", ".collide"]:
                shutil.move(
                    Path(str(f) + suf),
                    bundle / "uploads/discardedPages" / (f.name + suf),
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
        bundle_order = extract_order(fname)
        rmsg = scanMessenger.uploadCollidingPage(
            code,
            int(ts),
            int(ps),
            int(vs),
            fname,
            md5,
            bundle_name,
            bundle_order,
        )
        doFiling(rmsg, Path("bundles") / bundle_name, fname)


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
