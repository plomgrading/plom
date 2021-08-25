#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Randomly ID papers for testing purposes."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import random

from stdiomask import getpass

from plom.plom_exceptions import (
    PlomConflict,
    PlomExistingLoginException,
    PlomTakenException,
)
from plom.messenger import Messenger


def do_rando_identifying_backend(messenger):
    idList = messenger.IDrequestClasslist()

    while True:
        task = messenger.IDaskNextTask()
        if task is None:
            print("No more tasks.")
            break
        try:
            print("Identifying task ", task)
            imageList = messenger.IDclaimThisTask(task)
        except PlomTakenException:
            # task already taken.
            continue

        while True:
            try:
                sid, sname = random.choice(idList)
                sname += " [randomly chosen]"
                messenger.IDreturnIDdTask(task, sid, sname)
                break
            except PlomConflict:
                print("SID/SN {}/{} already used".format(sid, sname))


def do_rando_identifying(server, password, user):
    """Randomly associate papers with students: only for testing please."""
    if server and ":" in server:
        s, p = server.split(":")
        messenger = Messenger(s, port=p)
    else:
        messenger = Messenger(server)
    messenger.start()

    # If user not specified then default to scanner
    if not user:
        user = "scanner"

    if not password:
        password = getpass(f"Please enter the '{user}' password: ")

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
        exit(1)

    try:
        do_rando_identifying_backend(messenger)
    finally:
        messenger.closeUser()
        messenger.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform identifier tasks randomly, generally for testing."
    )

    parser.add_argument("-w", "--password", type=str)
    parser.add_argument("-u", "--user", type=str)
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help="Which server to contact.",
    )
    args = parser.parse_args()
    do_rando_identifying(args.server, args.password, args.user)
