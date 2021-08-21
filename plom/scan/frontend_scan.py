# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Plom tools for scanning tests and pushing to servers."""

from pathlib import Path
from warnings import warn

import toml

from plom.scan import (
    upload_unknowns,
    print_unknowns_warning,
    bundle_has_nonuploaded_unknowns,
    upload_collisions,
    print_collision_warning,
    bundle_has_nonuploaded_collisions,
)
from plom.scan import scansToImages
from plom.scan.scansToImages import process_scans
from plom.scan.bundle_utils import make_bundle_dir, bundle_name_and_md5_from_file
from plom.scan.bundle_utils import archivedir
from plom.scan.sendPagesToServer import does_bundle_exist_on_server
from plom.scan import sendPagesToServer
from plom.scan import readQRCodes


def processScans(server, password, pdf_fname, gamma, extractbmp):
    """Process PDF file into images and read QRcodes

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
    exists, reason = does_bundle_exist_on_server(bundle_name, md5, server, password)
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

    bundledir = Path("bundles") / bundle_name
    make_bundle_dir(bundledir)

    with open(bundledir / "source.toml", "w+") as f:
        toml.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    process_scans(pdf_fname, bundledir, not gamma, not extractbmp)
    print("Read QR codes")
    readQRCodes.processBitmaps(bundledir, server, password)
    # TODO: can collisions warning be written here too?
    if bundle_has_nonuploaded_unknowns(bundledir):
        print_unknowns_warning(bundledir)
        print('You can upload these by passing "--unknowns" to the upload command')


def uploadImages(
    server, password, bundle_name, unknowns_flag=False, collisions_flag=False
):
    """Upload processed images from bundle.

    Try to create a bundle on server.
    - abort if name xor md5sum of bundle known.
    - continue otherwise (server will give skip-list)
    Skip images whose page within the bundle is in the skip-list since
    those are already uploaded.
    Once uploaded archive the bundle pdf.

    As part of the upload 'unknown' pages and 'collisions' may be detected.
    These will not be uploaded unless the appropriate flags are set.
    """
    if bundle_name.lower().endswith(".pdf"):
        warn('Careful, the bundle name should not include ".pdf"')

    bundledir = Path("bundles") / bundle_name
    info = toml.load(bundledir / "source.toml")
    md5 = info["md5"]

    # TODO: check first to avoid misleading msg?
    print('Creating bundle "{}" on server'.format(bundle_name))
    rval = sendPagesToServer.createNewBundle(bundle_name, md5, server, password)
    # should be [True, skip_list] or [False, reason]
    if rval[0]:
        skip_list = rval[1]
        if len(skip_list) > 0:
            print("Some images from that bundle were uploaded previously:")
            print("Pages {}".format(skip_list))
            print("Skipping those images.")
    else:
        print("There was a problem with this bundle.")
        if rval[1] == "name":
            print("A different bundle with the same name was uploaded previously.")
        else:
            print(
                "A bundle with matching md5sum but different name was uploaded previously."
            )
        print("Stopping.")
        return

    print("Upload images to server")
    [TPN, updates] = sendPagesToServer.uploadTPages(
        bundledir, skip_list, server, password
    )
    print(
        "Tests were uploaded to the following studentIDs: {}".format(
            ", ".join(TPN.keys())
        )
    )
    print("Server reports {} papers updated.".format(updates))

    pdf_fname = Path(info["file"])
    if pdf_fname.exists():
        print(
            'Original PDF "{}" still in place: archiving to "{}"...'.format(
                pdf_fname, str(archivedir)
            )
        )
        scansToImages.archiveTBundle(pdf_fname)
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

    if unknowns_flag:
        if bundle_has_nonuploaded_unknowns(bundledir):
            print_unknowns_warning(bundledir)
            print("Unknowns upload flag present: uploading...")
            upload_unknowns(bundledir, server, password)
        else:
            print(
                "Unknowns upload flag present: but no unknowns - so no actions required."
            )
    else:
        if bundle_has_nonuploaded_unknowns(bundledir):
            print_unknowns_warning(bundledir)
            print('If you want to upload these unknowns, rerun with "--unknowns".')

    if collisions_flag:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            print("Collisions upload flag present.")
            # TODO:add a --yes flag?
            yn = input("Are you sure you want to upload these colliding pages? [y/N] ")
            if yn.lower() == "y":
                print("Proceeding.")
                upload_collisions(bundledir, server, password)
        else:
            print(
                "Collisions upload flag present: but no collisions - so no actions required."
            )
    else:
        if bundle_has_nonuploaded_collisions(bundledir):
            print_collision_warning(bundledir)
            print('If you want to upload these collisions, rerun with "--collisions".')
