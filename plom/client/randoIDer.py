#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald

"""Randomly ID papers for testing purposes."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and others"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import getpass
import random

from plom.plom_exceptions import (
    PlomConflict,
    PlomExistingLoginException,
    PlomTakenException,
)
from plom.messenger import Messenger

# -------------------------------------------


def startIdentifying():
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


# -------------------------------------------

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
    global messenger
    args = parser.parse_args()
    if args.server and ":" in args.server:
        s, p = args.server.split(":")
        messenger = Messenger(s, port=p)
    else:
        messenger = Messenger(args.server)
    messenger.start()

    # If user not specified then default to scanner
    if args.user is None:
        user = "scanner"
    else:
        user = args.user

    # get the password if not specified
    if args.password is None:
        pwd = getpass.getpass("Please enter the '{}' password:".format(user))
    else:
        pwd = args.password

    # get started
    try:
        messenger.requestAndSaveToken(user, pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            "This script has automatically force-logout'd that user."
        )
        messenger.clearAuthorisation(user, pwd)
        exit(1)

    spec = messenger.get_spec()

    try:
        startIdentifying()
    except Exception as e:
        print("Error identifying papers: {}".format(e))
        exit(1)

    messenger.closeUser()
    messenger.stop()
