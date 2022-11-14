# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import hashlib
import json
import logging
from pathlib import Path
import shutil
from textwrap import dedent

from plom.scan import with_scanner_messenger
from plom import PlomImageExts
from plom.scan.sendPagesToServer import extract_order


log = logging.getLogger("scan")


def doFiling(rmsg, bundle, f):
    if rmsg[0]:
        # should be [True, "success", message]
        assert rmsg[1] == "success"
        log.info("%s uploaded as CollidingPage.  Server says: %s", f, rmsg[2])
        # TODO: this didn't used to print: should it?  Unknown does...
        print(f"{f} uploaded as CollidingPage.")
        for suf in ["", ".qr", ".collide"]:
            shutil.move(
                Path(str(f) + suf),
                bundle / "uploads/sentPages/collisions" / (f.name + suf),
            )
    elif rmsg[1] == "duplicate":
        # should be [False, reason, message]
        # TODO: clarify is something happened or what?
        log.warning("Collision! TODO!, server msg: %s", rmsg[2])
        print(rmsg[2])
        for suf in ["", ".qr", ".collide"]:
            shutil.move(
                Path(str(f) + suf),
                bundle / "uploads/discardedPages" / (f.name + suf),
            )
    elif rmsg[1] == "original":
        raise RuntimeError(f"Unexpected code path that should not happen! msg={rmsg}")
    else:
        raise RuntimeError(f"Unexpected code path that should not happen! msg={rmsg}")


def sendCollidingFiles(scanMessenger, bundle_name, files):
    for f in files:
        with open(Path(str(f) + ".collide"), "r") as fh:
            cdat = json.load(fh)
        print(
            "Uploading {} which collides with {}, tpv = {} {} {}".format(
                f, cdat[0], cdat[1], cdat[2], cdat[3]
            )
        )
        ts = str(cdat[1]).zfill(4)
        ps = str(cdat[2]).zfill(2)
        vs = str(cdat[3])
        code = "t{}p{}v{}".format(ts, ps, vs)
        with open(f, "rb") as fh:
            md5 = hashlib.md5(fh.read()).hexdigest()
        bundle_order = extract_order(f)
        rmsg = scanMessenger.uploadCollidingPage(
            code,
            int(ts),
            int(ps),
            int(vs),
            f,
            md5,
            bundle_name,
            bundle_order,
        )
        doFiling(rmsg, Path("bundles") / bundle_name, f)


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


def list_bundle_nonuploaded_collisions(bundle_dir):
    """Uploading a bundle sometimes results in collisions: list them.

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        list(Path)
    """
    files = []
    for ext in PlomImageExts:
        files.extend((bundle_dir / "uploads/collidingPages").glob(f"*.{ext}"))
    return files


def count_bundle_nonuploaded_collisions(bundle_dir):
    """Uploading a bundle sometimes results in collisions: how many does this have?

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        int
    """
    return len(list_bundle_nonuploaded_collisions(bundle_dir))


def print_collision_warning(bundle_dir):
    """Print info about collisions and list of collisions in this bundle.

    Args:
        bundle_dir (str, Path): path to a bundle.
    """
    files = list_bundle_nonuploaded_collisions(bundle_dir)
    if not files:
        log.info("Processing resulted in **no** Colliding Pages")
        return
    log.info("Processing resulted in %s Colliding Pages", len(files))
    log.info("Collisions list:\n    " + "\n    ".join([x.name for x in files]))

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


@with_scanner_messenger
def upload_collisions(bundle_dir, *, msgr):
    if not bundle_dir.is_dir():
        raise ValueError("should've been a directory!")

    files = []
    for ext in PlomImageExts:
        files.extend((bundle_dir / "uploads/collidingPages").glob(f"*.{ext}"))
    sendCollidingFiles(msgr, bundle_dir.name, files)
