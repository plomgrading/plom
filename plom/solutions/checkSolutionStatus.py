# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


def checkStatus(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-solutions clear"'
        )
        raise

    try:
        solutionList = msgr.getSolutionStatus()
        return solutionList
    finally:
        msgr.closeUser()
        msgr.stop()
