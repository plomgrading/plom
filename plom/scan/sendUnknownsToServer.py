# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import hashlib
import logging
from pathlib import Path
import shutil

from plom.scan import with_scanner_messenger
from plom import PlomImageExts
from plom.scan.sendPagesToServer import extract_order


log = logging.getLogger("scan")


def doFiling(rmsg, bundle, f):
    if rmsg[0]:
        # should be [True, "success", message]
        assert rmsg[1] == "success"
        log.info("%s uploaded as UnknownPage.  Server says: %s", f, rmsg[2])
        # TODO: should this still print?  probably
        print(f"{f} uploaded as UnknownPage.")
        shutil.move(f, bundle / "uploads/sentPages/unknowns" / f.name)
        shutil.move(
            Path(str(f) + ".qr"),
            bundle / "uploads/sentPages/unknowns" / f"{f.name}.qr",
        )
    elif rmsg[1] == "duplicate":
        # should be [False, reason, message]
        # TODO: clarify is something happened or what?
        log.warning("Duplicate! TODO, server msg: %s", rmsg[2])
        print(rmsg[2])
        shutil.move(f, bundle / "uploads/discardedPages" / f.name)
        shutil.move(
            Path(str(f) + ".qr"),
            bundle / "uploads/discardedPages" / f"{f.name}.qr",
        )
    else:
        raise RuntimeError(f"Unexpected code path that should not happen! msg={rmsg}")


def sendUnknownFiles(msgr, bundle_name, files):
    for f in files:
        with open(f, "rb") as fh:
            md5 = hashlib.md5(fh.read()).hexdigest()
        order = extract_order(f)
        bundle_order = order
        rmsg = msgr.uploadUnknownPage(f, order, md5, bundle_name, bundle_order)
        doFiling(rmsg, Path("bundles") / bundle_name, f)


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


def list_bundle_nonuploaded_unknowns(bundle_dir):
    """List any non-uploaded unknown pages that this bundle has.

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        list: of ``pathlib.Path`` objects
    """
    bundle_dir = Path(bundle_dir)
    files = []
    # Look for pages in unknowns
    for ext in PlomImageExts:
        files.extend((bundle_dir / "unknownPages").glob(f"*.{ext}"))
    return files


def count_bundle_nonuploaded_unknowns(bundle_dir):
    """How many non-uploaded unknown pages does this bundle have.

    Args:
        bundle_dir (str, Path): path to a bundle.

    Return:
        int
    """
    return len(list_bundle_nonuploaded_unknowns(bundle_dir))


def print_unknowns_warning(bundle_dir):
    """Print info about unknowns and list of unknowns in this bundle.

    Args:
        bundle_dir (str, Path): path to a bundle.
    """
    files = list_bundle_nonuploaded_unknowns(bundle_dir)
    if not files:
        log.info("Processing resulted in **no** UnknownPages")
        return
    log.info("Processing resulted in %s UnknownPages", len(files))
    log.info("Unknowns list:\n    " + "\n    ".join([x.name for x in files]))

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


@with_scanner_messenger
def upload_unknowns(bundle_dir, *, msgr):
    if not bundle_dir.is_dir():
        raise ValueError("should've been a directory!")
    files = []
    # Look for pages in unknowns
    for ext in PlomImageExts:
        files.extend((bundle_dir / "unknownPages").glob(f"*.{ext}"))
    sendUnknownFiles(msgr, bundle_dir.name, files)
