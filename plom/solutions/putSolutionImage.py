# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass

from plom.messenger import ManagerMessenger


def putSolutionImage(
    question,
    version,
    imageName,
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

    managerMessenger.putSolutionImage(question, version, image)
    managerMessenger.stop()
