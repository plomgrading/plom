# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import hashlib
import shutil
from pathlib import Path

from plom.scan import with_scanner_messenger
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


@with_scanner_messenger
def upload_unknowns(bundle_dir, *, msgr):
    if not bundle_dir.is_dir():
        raise ValueError("should've been a directory!")
    files = []
    # Look for pages in unknowns
    for ext in PlomImageExts:
        files.extend((bundle_dir / "unknownPages").glob("*.{}".format(ext)))
    sendUnknownFiles(msgr, bundle_dir.name, files)
