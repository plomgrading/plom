# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from plom.messenger import ScanMessenger
from plom.plom_exceptions import PlomExistingLoginException


def get_bundle_list(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("scanner", pwd)
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
        bundle_list = msgr.listBundles()
    finally:
        msgr.closeUser()
        msgr.stop()

    return bundle_list


def print_bundle_list(server=None, password=None):
    # TODO - sort list by filename?

    bundle_list = get_bundle_list(server, password)
    if len(bundle_list) == 0:
        print("No bundles in database.")
        return

    print("Name\tnumberOfPages\tmd5sum")
    for X in bundle_list:
        print(f"{X['name']}\t{X['numberOfPages']}\t{X['md5sum']}")
