# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2022 Natalia Accomazzo Scotti

"""Plom tools for scanning tests and pushing to servers.

There are two main approaches to uploading: Test Pages and Homework Pages.
This module deals with Test Pages: these are usually bundles of pages
(pdf files) that typically have QR-codes but may not (yet) be associated
with a particular student.  In theory these mostly map onto expected blank
pages that the server is aware of (from exam creation time).

In contrast, Homework pages are associated with a particular student, for
example, each student has uploaded a self-scanned bundle (pdf file) of
their work.  But the precise relationship between this work and questions
in the exam is less clear.  For these, see :py:module:`frontend_hwscan`.
"""

import logging
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

from plom.misc_utils import format_int_list_with_runs
from plom.scan.sendUnknownsToServer import (
    upload_unknowns,
    print_unknowns_warning,
    bundle_has_nonuploaded_unknowns,
)
from plom.scan.sendCollisionsToServer import (
    upload_collisions,
    print_collision_warning,
    bundle_has_nonuploaded_collisions,
)
from plom.scan.sendPagesToServer import (
    does_bundle_exist_on_server,
    createNewBundle,
    uploadTPages,
)
from plom.scan.bundle_utils import (
    get_bundle_dir,
    bundle_name_and_md5_from_file,
    archivedir,
    archiveTBundle,
)
from plom.scan.scansToImages import process_scans
from plom.scan import readQRCodes


log = logging.getLogger("scan")


def processScans(
    pdf_fname,
    *,
    msgr,
    gamma: bool = False,
    extractbmp: bool = False,
    demo: bool = False,
):
    """Process PDF file into images and read QRcodes.

    Args:
        pdf_fname (pathlib.Path/str): path to a PDF file.  Need not be in
            the current working directory.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        gamma: do gamma correction
        extractbmp: whether to try extracting bitmaps instead of the default
            of rendering the page image.
        demo: do things appropriate for a demo such as lower quality
            or various simulated rotations.

    Returns:
        None

    Convert file into a bundle-name
    Check with server if bundle/md5 already on server
    - abort if name xor md5sum known.
    - continue if neither known or both known
    Make required directories for processing bundle,
    convert PDF to images and read QR codes from those.
    """
    pdf_fname = Path(pdf_fname)
    bundle_name, md5 = bundle_name_and_md5_from_file(pdf_fname)

    new_bundle = True
    print(f'Checking if bundle "{bundle_name}" already exists on server')
    exists, reason = does_bundle_exist_on_server(bundle_name, md5, msgr=msgr)
    if exists:
        if reason == "name":
            print(
                f'The bundle "{bundle_name}" has been used previously for a different bundle. Stopping'
            )
            return
        elif reason == "md5sum":
            print(
                "A bundle with matching md5sum is already in system with a different name. Stopping"
            )
            return
        elif reason == "both":
            new_bundle = False
        else:
            raise RuntimeError("Should not be here: unexpected code path!")

    bundledir = get_bundle_dir(bundle_name)

    logfile = bundledir / "processing.log"
    print(f"Logging details to {logfile}")
    logging.basicConfig(
        format="%(asctime)s %(levelname)5s:%(name)s\t%(message)s",
        datefmt="%b%d %H:%M:%S %Z",
        filename=logfile,
    )
    logging.getLogger().setLevel("INFO")
    if new_bundle:
        log.info(f'Starting processing new bundle "{bundle_name}", {md5}')
    else:
        m = f'bundle "{bundle_name}" {md5} previously declared: you are likely trying again after a crash.'
        print(f"Warning {m}")
        log.warning(m)

    with open(bundledir / "source.toml", "w") as f:
        tomlkit.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    process_scans(pdf_fname, bundledir, not gamma, not extractbmp, demo=demo)
    print("Read QR codes")
    readQRCodes.processBitmaps(bundledir, msgr=msgr)
    # TODO: can collisions warning be written here too?
    if bundle_has_nonuploaded_unknowns(bundledir):
        print_unknowns_warning(bundledir)
        print('You can upload these by passing "--unknowns" to the upload command')


def uploadImages(
    bundle_name: str,
    *,
    msgr,
    do_unknowns: bool = False,
    do_collisions: bool = False,
    prompt: bool = True,
) -> None:
    """Upload processed images from bundle.

    Args:
        bundle_name: usually the PDF filename but in general whatever
            string was used to define a bundle.  Do not send a path.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        do_unknowns: upload any unknown images.
        do_collisions: upload any colliding images.
        prompt: ok to interactively prompt (default: True).

    Returns:
        None

    Try to create a bundle on server.
    - abort if name xor md5sum of bundle known.
    - continue otherwise (server will give skip-list)
    Skip images whose page within the bundle is in the skip-list since
    those are already uploaded.
    Once uploaded archive the bundle pdf.

    As part of the upload 'unknown' pages and 'collisions' may be detected.
    These will not be uploaded unless the appropriate flags are set.
    """
    assert (
        Path(bundle_name).name == bundle_name
    ), f'bundle name "{bundle_name}" should be just the filename, no path'
    bundledir = get_bundle_dir(bundle_name)
    with open(bundledir / "source.toml", "rb") as f:
        info = tomllib.load(f)
    md5 = info["md5"]

    logfile = bundledir / "processing.log"
    print(f"Logging details to {logfile}")
    logging.basicConfig(
        format="%(asctime)s %(levelname)5s:%(name)s\t%(message)s",
        datefmt="%b%d %H:%M:%S %Z",
        filename=logfile,
    )
    logging.getLogger().setLevel("INFO")

    log.info(f'Trying to create bundle "{bundle_name}" on server')
    exists, extra = createNewBundle(bundle_name, md5, msgr=msgr)
    # should be (True, skip_list) or (False, reason)
    if exists:
        skip_list = extra
        if len(skip_list) > 0:
            msg = "Some images from that bundle were previously uploaded"
            print(msg)
            print(
                "Skipping previously uploaded pages: "
                + ", ".join(str(x) for x in skip_list)
            )
            log.warning(msg)
            log.warning(
                "Skipping previous uploaded pages:\n  %s",
                "\n  ".join(str(x) for x in skip_list),
            )
    else:
        print("There was a problem with this bundle.")
        if extra == "name":
            msg = "A different bundle with the same name was uploaded previously."
            msg += " Aborting bundle upload."
            print(msg)
            log.error(msg)
            return
        elif extra == "md5sum":
            msg = "Differently-named bundle with same md5sum previously uploaded."
            msg += " Aborting bundle upload."
            print(msg)
            log.error(msg)
            return
        else:
            msg = "Should not be here: unexpected code path! File issue"
            log.error(msg)
            raise RuntimeError(msg)

    print(f"Upload images to server from {bundledir}")
    log.info("Upload images to server from %s", bundledir)
    TPN = uploadTPages(bundledir, skip_list, msgr=msgr)
    _fmt_list = format_int_list_with_runs(TPN.keys(), zero_padding=4)
    msg = f"Tests were uploaded to the following papers: {_fmt_list}"
    print(msg)
    log.info(msg)

    pdf_fname = Path(info["file"])
    if pdf_fname.exists():
        msg = f'Original PDF "{pdf_fname}" still in place: archiving to "{archivedir}"'
        print(msg)
        log.info(msg)
        archiveTBundle(pdf_fname)
    elif (archivedir / pdf_fname).exists():
        msg = f'Original PDF "{pdf_fname}" is already archived in "{archivedir}"'
        print(msg)
        log.info(msg)
    else:
        raise RuntimeError("Did you move the archived PDF?  Please don't do that!")

    # Note: no need to "finalize" a bundle, its ok to send unknown/collisions
    # after the above call to sendPagesToServer.

    if do_unknowns:
        if bundle_has_nonuploaded_unknowns(bundledir):
            msg = "Unknowns upload flag present: uploading..."
            print(msg)
            log.info(msg)
            upload_unknowns(bundledir, msgr=msgr)
        else:
            m = "Unknowns upload flag present: but no unknowns - no action required."
            print(m)
            log.info(m)

    else:
        if bundle_has_nonuploaded_unknowns(bundledir):
            print_unknowns_warning(bundledir)
            print('If you want to upload these unknowns, rerun with "--unknowns".')

    if do_collisions:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            doit = False
            if not prompt:
                m = "Collisions upload flag present and prompts disabled: uploading..."
                log.info(m)
                print(m)
                doit = True
            else:
                log.info(
                    "Collisions upload flag present w/ interactive prompts enabled"
                )
                print("Collisions upload flag present.")
                yn = input(
                    "Are you sure you want to upload these colliding pages? [y/N] "
                )
                if yn.lower() == "y":
                    print("Proceeding.")
                    doit = True
            if doit:
                upload_collisions(bundledir, msgr=msgr)
        else:
            m = "Collisions upload flag present: but no collisions - no action required."
            print(m)
            log.info(m)

    else:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            print('If you want to upload these collisions, rerun with "--collisions".')
