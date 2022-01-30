# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Randomly ID papers for testing purposes."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import random

from plom.plom_exceptions import (
    PlomConflict,
    PlomExistingLoginException,
    PlomTakenException,
)
from plom.messenger import Messenger


def do_rando_identifying_backend(messenger):
    classlist = messenger.IDrequestClasslist()

    while True:
        task = messenger.IDaskNextTask()
        if task is None:
            print("No more tasks.")
            break
        try:
            print("Identifying task ", task)
            messenger.IDclaimThisTask(task)
        except PlomTakenException:
            # task already taken.
            continue

        while True:
            try:
                person = random.choice(classlist)
                name = person["studentName"] + " [randomly chosen]"
                messenger.IDreturnIDdTask(task, person["id"], name)
                break
            except PlomConflict:
                print(f"Already used: {person}")


def do_rando_identifying(server, user, password):
    """Randomly associate papers with students: only for testing please.

    args:
        server (str)
        user (str)
        password (str)

    returns:
        int: 0 on success, non-zero on error/unexpected.
    """
    if server and ":" in server:
        s, p = server.split(":")
        messenger = Messenger(s, port=p)
    else:
        messenger = Messenger(server)
    messenger.start()

    try:
        messenger.requestAndSaveToken(user, password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "This script has automatically force-logout'd that user."
        )
        messenger.clearAuthorisation(user, password)
        return 1

    try:
        do_rando_identifying_backend(messenger)
    finally:
        messenger.closeUser()
        messenger.stop()
    return 0
