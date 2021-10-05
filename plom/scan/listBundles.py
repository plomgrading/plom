# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from plom.messenger import ScanMessenger


def get_bundle_list(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger = ScanMessenger(s, port=p)
    else:
        scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    try:
        bundle_list = scanMessenger.listBundles()
    finally:
        scanMessenger.closeUser()
        scanMessenger.stop()

    return bundle_list


def print_bundle_list(server=None, password=None):
    bundle_list = get_bundle_list(server, password)
    for X in bundle_list:
        print(f"{X['name']}\t{X['numberOfPages']}\t{X['md5sum']}")
