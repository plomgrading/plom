# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald

from plom.messenger import ManagerMessenger


def clearLogin(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        managerMessenger = ManagerMessenger(s, port=p)
    else:
        managerMessenger = ManagerMessenger(server)
    managerMessenger.start()

    managerMessenger.clearAuthorisation("manager", password)
    print("Manager login cleared.")
    managerMessenger.stop()
