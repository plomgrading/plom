#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import csv
import getpass
import json
import os
import random
import sys
import tempfile
import toml

from plom.plom_exceptions import *
from plom import __version__, Plom_API_Version
from plom.messenger import Messenger

# -------------------------------------------


def startIdentifying():
    csvfile = messenger.IDrequestClasslist()
    idList = []
    reader = csv.DictReader(csvfile, skipinitialspace=True)
    for row in reader:
        idList.append([row["id"], row["studentName"]])

    while True:
        task = messenger.IDaskNextTask()
        if task is None:
            print("No more tasks.")
            break
        try:
            print("Identifying task ", task)
            imageList = messenger.IDclaimThisTask(task)
        except PlomBenignException as err:
            # task already taken.
            continue

        while True:
            try:
                c = random.choice(idList)
                c[1] += " [randomly chosen]"
                messenger.IDreturnIDdTask(task, c[0], c[1])
                break
            except PlomBenignException as e:
                print("SID/SN {}/{} already used".format(c[0], c[1]))


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

    spec = messenger.getInfoGeneral()

    print(spec)

    try:
        startIdentifying()
    except Exception as e:
        print("Error identifying papers: {}".format(e))
        exit(1)

    messenger.closeUser()
    messenger.stop()

    exit(0)
