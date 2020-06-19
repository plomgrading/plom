# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import sys
from getpass import getpass

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException, PlomConflict


def upload_classlist(classlist, server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        # TODO: bit annoying, maybe want manager UI open...
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another management tool running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-build clear"'
        )
        sys.exit(10)
    try:
        msgr.upload_classlist(classlist)
    except PlomConflict:
        print("Error: Server already has a classlist, see help (TODO: add force?).")
        sys.exit(3)
    finally:
        msgr.closeUser()
        msgr.stop()
