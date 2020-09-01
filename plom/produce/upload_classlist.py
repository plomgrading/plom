# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

import sys
from getpass import getpass

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException, PlomConflict


def get_messenger(server=None, password=None):
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

    return msgr


def upload_classlist(classlist, msgr):
    """Uploads a classlist file to the server.

    Arguments:
        classdict (list): list of (str, str) pairs of the form
                (student ID, student name).
        msgr (ManagerMessenger): an already-connected messenger object for
                talking to the server.


    """

    try:
        msgr.upload_classlist(classlist)
    except PlomConflict:
        print("Error: Server already has a classlist, see help (TODO: add force?).")
        sys.exit(3)
    finally:
        msgr.closeUser()
        msgr.stop()
