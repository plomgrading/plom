# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021, 2023 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from plom.messenger import ScanMessenger


def clear_login(server=None, password=None):
    scanMessenger = ScanMessenger(server)
    scanMessenger.start()

    try:
        scanMessenger.clearAuthorisation("scanner", password)
        print("Scanner login cleared.")
    finally:
        scanMessenger.stop()
