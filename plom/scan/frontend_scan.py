# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

"""Plom tools for scanning tests and pushing to servers.

There are two main approaches to uploading: Test Pages and Homework Pages.
This module deals with Test Pages: these are usually bundles of pages
(pdf files) that typically have QR-codes but may not (yet) be associated
with a particular student.  In theory these mostly map onto expected blank
pages that the server is aware of (from exam creation time).

In contrast, Homework pages are associated with a paricular student, for
example, each student has uploaded a self-scanned bundle (pdf file) of
their work.  But the precise relationship between this work and questions
in the exam is less clear.  For these, see :py:module:`frontend_hwscan`.
"""

from pathlib import Path

import toml

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


def processScans(pdf_fname, *, msgr, gamma=False, extractbmp=False, demo=False):
    """Process PDF file into images and read QRcodes

    args:
        pdf_fname (pathlib.Path/str): path to a PDF file.  Need not be in
            the current working directory.

    keyword args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        bundle_name (str/None): Override the bundle name (which is by
            default is generated from the PDF filename).
        gamma (bool):
        extractbmp (bool):
        demo (bool): do things appropriate for a demo such as lower quality
            or various simulated rotations.

    return:
        None

    Convert file into a bundle-name
    Check with server if bundle/md5 already on server
    - abort if name xor md5sum known.
    - continue if neither known or both known
    Make required directories for processing bundle,
    convert PDF to images and read QR codes from those.
    """
    pdf_fname = Path(pdf_fname)
    if not pdf_fname.is_file():
        print("Cannot find file {} - skipping".format(pdf_fname))
        return
    # TODO: replace above with letting exception rise from next:
    bundle_name, md5 = bundle_name_and_md5_from_file(pdf_fname)

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
            print(
                f'Warning - bundle "{bundle_name}" has been declared previously - you are likely trying again as a result of a crash. Continuing'
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path!")

    bundledir = get_bundle_dir(bundle_name)

    with open(bundledir / "source.toml", "w") as f:
        toml.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    process_scans(pdf_fname, bundledir, not gamma, not extractbmp, demo=demo)
    print("Read QR codes")
    readQRCodes.processBitmaps(bundledir, msgr=msgr)
    # TODO: can collisions warning be written here too?
    if bundle_has_nonuploaded_unknowns(bundledir):
        print_unknowns_warning(bundledir)
        print('You can upload these by passing "--unknowns" to the upload command')


def uploadImages(bundle_name, *, msgr, do_unknowns=False, do_collisions=False):
    """Upload processed images from bundle.

    args:
        server (str)
        password (str)
        bundle_name (str): usually the PDF filename but in general
            whatever string was used to define a bundle.

    keyword args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        do_unknowns (bool):
        do_collisions (bool):

    return:
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
    bundledir = Path("bundles") / bundle_name
    info = toml.load(bundledir / "source.toml")
    md5 = info["md5"]

    print(f'Trying to create bundle "{bundle_name}" on server')
    exists, extra = createNewBundle(bundle_name, md5, msgr=msgr)
    # should be (True, skip_list) or (False, reason)
    if exists:
        skip_list = extra
        if len(skip_list) > 0:
            print("Some images from that bundle were uploaded previously:")
            print("Pages {}".format(skip_list))
            print("Skipping those images.")
    else:
        print("There was a problem with this bundle.")
        if extra == "name":
            print("A different bundle with the same name was uploaded previously.")
        elif extra == "md5sum":
            print("Differently-named bundle with same md5sum previously uploaded.")
        else:
            raise RuntimeError("Should not be here: unexpected code path! File issue")
        print("Aborting this bundle upload early!")
        return

    print("Upload images to server")
    TPN = uploadTPages(bundledir, skip_list, msgr=msgr)
    print(
        "Tests were uploaded to the following studentIDs: {}".format(
            ", ".join(TPN.keys())
        )
    )

    pdf_fname = Path(info["file"])
    if pdf_fname.exists():
        print(
            'Original PDF "{}" still in place: archiving to "{}"...'.format(
                pdf_fname, str(archivedir)
            )
        )
        archiveTBundle(pdf_fname)
    elif (archivedir / pdf_fname).exists():
        print(
            'Original PDF "{}" is already archived in "{}".'.format(
                pdf_fname, str(archivedir)
            )
        )
    else:
        raise RuntimeError("Did you move the archived PDF?  Please don't do that!")

    # Note: no need to "finalize" a bundle, its ok to send unknown/collisions
    # after the above call to sendPagesToServer.

    if do_unknowns:
        if bundle_has_nonuploaded_unknowns(bundledir):
            print_unknowns_warning(bundledir)
            print("Unknowns upload flag present: uploading...")
            upload_unknowns(bundledir, msgr=msgr)
        else:
            print(
                "Unknowns upload flag present: but no unknowns - so no actions required."
            )
    else:
        if bundle_has_nonuploaded_unknowns(bundledir):
            print_unknowns_warning(bundledir)
            print('If you want to upload these unknowns, rerun with "--unknowns".')

    if do_collisions:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            print("Collisions upload flag present.")
            # TODO:add a --yes flag?
            yn = input("Are you sure you want to upload these colliding pages? [y/N] ")
            if yn.lower() == "y":
                print("Proceeding.")
                upload_collisions(bundledir, msgr=msgr)
        else:
            print(
                "Collisions upload flag present: but no collisions - so no actions required."
            )
    else:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            print('If you want to upload these collisions, rerun with "--collisions".')
