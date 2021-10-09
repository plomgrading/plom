# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

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
            'In order to force-logout the existing authorisation run "plom-solution clear"'
        )
        raise

    try:
        success = msgr.deleteSolutionImage(question, version)
    except PlomNoSolutionException as err:
        print("No solution for question {} version {}".format(question, version))
        return None

    msgr.closeUser()
    msgr.stop()
    return success
