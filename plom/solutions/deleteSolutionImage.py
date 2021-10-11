# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException, PlomNoSolutionException


def deleteSolutionImage(
    question,
    version,
    server=None,
    password=None,
):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", password)
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
        success = msgr.deleteSolutionImage(question, version)
        return success
    except PlomNoSolutionException:
        print("No solution for question {} version {}".format(question, version))
        return None
    finally:
        msgr.closeUser()
        msgr.stop()
