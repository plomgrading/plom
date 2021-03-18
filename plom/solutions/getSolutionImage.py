# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass

from plom.messenger import ManagerMessenger


def getSolutionImage(
    question,
    version,
    server=None,
    password=None,
):
    if server and ":" in server:
        s, p = server.split(":")
        managerMessenger = ManagerMessenger(s, port=p)
    else:
        managerMessenger = ManagerMessenger(server)
    managerMessenger.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
            exit(1)
    else:
        pwd = password

    try:
        img = managerMessenger.getSolutionImage(question, version)
    except PlomBenignException as err:
        print("No solution for question {} version {}".format(question, version))
        return None
    managerMessenger.stop()
    return img
