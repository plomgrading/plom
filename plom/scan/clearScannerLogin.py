#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass

import plom.scanMessenger as scanMessenger


def clearLogin(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        scanMessenger.startMessenger(s, port=p)
    else:
        scanMessenger.startMessenger(server)

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    # get started

    scanMessenger.clearAuthorisation("scanner", pwd)
    print("Scanner login cleared.")
    scanMessenger.stopMessenger()
