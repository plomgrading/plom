# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

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
    bundle_list = get_bundle_list(server, password)
    if len(bundle_list) == 0:
        print("No bundles in database.")
        return

    bundle_list.sort(key=lambda X: X["name"])

    head = ["Name", "no. Pages", "md5sum"]
    print(f"{head[0]:40} | {head[1]:10} | {head[2]:32}")
    for X in bundle_list:
        if X["name"] == "__replacements__system__":
            print("-" * 90)
            print(
                "vvvvvvvv This bundle is autogenerated for plom system use only. vvvvvvvv"
            )
        #
        if X["md5sum"] == None:
            X["md5sum"] = "None"
        print(f"{X['name']:40} | {X['numberOfPages']:10} | {X['md5sum']:32}")
        #
        if X["name"] == "__replacements__system__":
            print("-" * 90)