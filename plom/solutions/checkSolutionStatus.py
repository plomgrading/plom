# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import getpass

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


def checkStatus(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not pwd:
        pwd = getpass.getpass("Please enter the 'manager' password:")

    # get started
    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException as e:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        exit(10)

    spec = msgr.get_spec()

    solutionList = msgr.getSolutionStatus()
    msgr.closeUser()
    msgr.stop()
    return solutionList
