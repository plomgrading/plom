#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning tests and pushing to servers.

## Overview of the scanning process

  1. Decide on a working directory for your scans, copy your PDFs into
     that directory and then cd into it.

  2. Use the `process` command to split your first PDF into bitmaps of
     each page.  This will also read any QR codes from the pages and
     match these against expectations from the server.

  3. Use the `upload` command to send pages to the server.  There are
     additional flags for dealing with special cases:

       a. Pages that could not be identified are called "Unknowns".
          They can include "Extra Pages" without QR codes, poor-quality
          scans where the QR reader failed, folded papers, etc.  A small
          number is normal but large numbers are cause for concern and
          sanity checking.  A human will (eventually) have to identify
          these manually.

       b. If the system detects you trying to upload a test page
          corresponding to one already in the system (but not identical)
          then those pages are filed as "Collisions". If you have good
          paper-handling protocols then this should not happen, except
          in exceptional circumstances (such as rescanning an illegible
          page).  Force the upload these if you really need to; the
          manager will then have to look at them.

  4. Run "plom-scan status" to get a brief summary of scanning to date.

  5. If something goes wrong such as crashes or interruptions, you may
     need to clear the "scanner" login with the `clear` command.

  These steps may be repeated as new PDF files come in: it is not
  necessary to wait until scanning is complete to start processing and
  uploading.
"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
from pathlib import Path
from warnings import warn

import toml

from plom import __version__
from plom.scan import (
    upload_unknowns,
    print_unknowns_warning,
    bundle_has_nonuploaded_unknowns,
    upload_collisions,
    print_collision_warning,
    bundle_has_nonuploaded_collisions,
    bundle_name_and_md5,
)


# TODO: this bit of code from messenger could be useful here
#    if os.path.isfile("server.toml"):
#        with open("server.toml") as fh:
#            si = toml.load(fh)
#        server = si["server"]
#        if server and ":" in server:
#            server, message_port = server.split(":")


# TODO: make some common util file to store all these names?
archivedir = Path("archivedPDFs")


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def make_required_directories(bundle=None):
    os.makedirs(archivedir, exist_ok=True)
    os.makedirs("bundles", exist_ok=True)
    # TODO: split up a bit, above are global, below per bundle
    if bundle:
        directory_list = [
            "uploads/sentPages",
            "uploads/discardedPages",
            "uploads/collidingPages",
            "uploads/sentPages/unknowns",
            "uploads/sentPages/collisions",
        ]
        for dir in directory_list:
            os.makedirs(bundle / Path(dir), exist_ok=True)


def processScans(server, password, pdf_fname, gamma, extractbmp):
    """Process PDF file into images and read QRcodes

    Convert file into a bundle-name
    Check with server if bundle/md5 already on server
    - abort if name xor md5sum known.
    - continue if neither known or both known
    Make required directories for processing bundle,
    convert PDF to images and read QR codes from those.
    """
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer
    from plom.scan import readQRCodes

    pdf_fname = Path(pdf_fname)
    if not pdf_fname.is_file():
        print("Cannot find file {} - skipping".format(pdf_fname))
        return
    # TODO: replace above with letting exception rise from next:
    bundle_name, md5 = bundle_name_and_md5(pdf_fname)
    # TODO: doesBundleExist(bundle_name, md5)

    print("Checking if bundle {} already exists on server".format(bundle_name))
    bundle_exists = sendPagesToServer.doesBundleExist(pdf_fname, server, password)
    # return [False, name], [True, name], [True,md5sum] or [True, both]
    if bundle_exists[0]:
        if bundle_exists[1] == "name":
            print(
                "The bundle name {} has been used previously for a different bundle. Stopping".format(
                    pdf_fname
                )
            )
            return
        elif bundle_exists[1] == "md5sum":
            print(
                "A bundle with matching md5sum is already in system with a different name. Stopping"
            )
            return
        elif bundle_exists[1] == "both":
            print(
                "Warning - bundle {} has been declared previously - you are likely trying again as a result of a crash. Continuing".format(
                    bundle_name
                )
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path!")

    bundledir = Path("bundles") / bundle_name
    make_required_directories(bundledir)

    with open(bundledir / "source.toml", "w+") as f:
        toml.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    scansToImages.processScans(pdf_fname, bundledir, not gamma, not extractbmp)
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
    from plom.scan import sendPagesToServer, scansToImages

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


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command")

spP = sub.add_parser(
    "process",
    help="Process scanned PDF to images and read QRs",
    description="Process one scanned PDF into page images, read QR codes and check info with server (e.g., versions match).",
)
spU = sub.add_parser(
    "upload",
    help="Upload page images to scanner",
    description="Upload page images to scanner.",
)
spS = sub.add_parser(
    "status",
    help="Get scanning status report from server",
    description="Get scanning status report from server.",
)
spC = sub.add_parser(
    "clear",
    help='Clear "scanner" login',
    description='Clear "scanner" login after a crash or other expected event.',
)
# TODO: maybe in the future?
# spA = sub.add_parser(
#     "all",
#     help="Process, read and upload page images to scanner (WIP!)",
#     description="Process, read and upload page images to scanner. CAUTION: Work in Progress!",
# )
# spA.add_argument("scanPDF", nargs="+", help="The PDF(s) containing scanned pages.")
spP.add_argument("scanPDF", help="The PDF file of scanned pages.")
g = spP.add_mutually_exclusive_group(required=False)
g.add_argument(
    "--gamma-shift",
    action="store_true",
    dest="gamma",
    help="""
        Apply white balancing to the scan, if the image format is
        lossless (PNG).
        By default, this gamma shift is NOT applied; this is because it
        may worsen some poor-quality scans with large shadow regions.
    """,
)
g.add_argument(
    "--no-gamma-shift",
    action="store_false",
    dest="gamma",
    help="Do not apply white balancing.",
)
g = spP.add_mutually_exclusive_group(required=False)
g.add_argument(
    "--extract-bitmaps",
    action="store_true",
    dest="extractbmp",
    help="""
        If a PDF page seems to contain exactly one bitmap image and
        nothing else, then extract that losslessly instead of rendering
        the page as a new PNG file.  This will typically give nicer
        images for the common scan case where pages are simply JPEG
        images.  But some care must be taken that the image is not
        annotated in any way and that no other markings appear on the
        page.
        As the algorithm to decide this is NOT YET IDEAL, this is
        currently OFF BY DEFAULT, but we anticipate it being the default
        in a future version.
    """,
)
g.add_argument(
    "--no-extract-bitmaps",
    action="store_false",
    dest="extractbmp",
    help="""
        Don't try to extract bitmaps; just render each page.  This is
        safer but not always ideal for image quality.
    """,
)

spU.add_argument("bundleName", help="The name of the PDF file, without extension.")
spU.add_argument(
    "-u",
    "--unknowns",
    action="store_true",
    help='Upload "unknowns", pages from which the QR-codes could not be read.',
)
spU.add_argument(
    "-c",
    "--collisions",
    action="store_true",
    help='Upload "collisions", pages which appear to already be on the server. '
    + "You should not need this option except under exceptional circumstances.",
)
for x in (spU, spS, spC, spP):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_SCAN_PASSWORD"]
        except KeyError:
            pass

    if args.command == "process":
        processScans(
            args.server, args.password, args.scanPDF, args.gamma, args.extractbmp
        )
    elif args.command == "upload":
        uploadImages(
            args.server, args.password, args.bundleName, args.unknowns, args.collisions
        )
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
