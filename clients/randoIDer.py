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


from plom_exceptions import *
import messenger


sys.path.append("..")  # this allows us to import from ../resources
from resources.version import __version__
from resources.version import Plom_API_Version

lastTime = {}


def readLastTime():
    """Read the login + server options that were used on
    the last run of the client.
    """
    global lastTime
    # set some reasonable defaults.
    lastTime["user"] = ""
    lastTime["server"] = "localhost"
    lastTime["mport"] = "41984"
    lastTime["pg"] = 1
    lastTime["v"] = 1
    lastTime["fontSize"] = 10
    lastTime["upDown"] = "up"
    lastTime["mouse"] = "right"
    # If config file exists, use it to update the defaults
    if os.path.isfile("plomConfig.toml"):
        with open("plomConfig.toml") as data_file:
            lastTime.update(toml.load(data_file))


def writeLastTime():
    """Write the options to the config file."""
    fh = open("plomConfig.toml", "w")
    fh.write(toml.dumps(lastTime))
    fh.close()


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

        n = 0
        while True:
            n += 1
            try:
                if n > 5 and random.random() < 0.5:
                    # after a while, choose non-ascii 50% of time
                    c = idList[14]
                c = random.choice(idList)
                print(c)
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
        "-s", "--server", help="Which server to contact (must specify port as well)."
    )
    parser.add_argument(
        "-p", "--port", help="Which port to use (must specify server as well)."
    )
    args = parser.parse_args()
    # must spec both server+port or neither.
    if args.server and args.port:
        messenger.startMessenger(altServer=args.server, altPort=args.port)
    elif args.server is None and args.port is None:
        messenger.startMessenger()
    else:
        print("You must specify both the server and the port. Quitting.")
        exit(1)

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
    messenger.stopMessenger()

    exit(0)
