#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import getpass
import json
import os
import random
import sys
import tempfile
import toml

from plom import __version__, Plom_API_Version
from plom.plom_exceptions import *
from plom.messenger import ManagerMessenger


# -------------------------------------------
# This is a very very cut-down version of annotator
# So we can automate some random marking of papers


def startReverting(question, version):
    print(
        "Starting to revert all done tasks for question {} version {}".format(
            question, version
        )
    )
    tasksToRevert = messenger.RgetMarked(q, v)
    print("Tasks to revert  = ", tasksToRevert)
    for task in tasksToRevert:
        try:
            messenger.MrevertTask(task)
        except Exception as err:
            print("Error trying to revert task {} = {}".format(task, err))
            exit(1)


# -------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Revert all the graded papers.  DANGEROUS: intended for testing."
    )

    parser.add_argument("-w", "--password", type=str)
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
        messenger = ManagerMessenger(s, port=p)
    else:
        messenger = ManagerMessenger(args.server)
    messenger.start()

    user = "manager"

    # get the password if not specified
    if args.password is None:
        try:
            pwd = getpass.getpass("Please enter the '{}' password:".format(user))
        except Exception as error:
            print("Password entry error = ", error)
            exit(1)
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

    try:
        spec = messenger.get_spec()
    except Exception as e:
        print("Error getting general info from server = ", e)
        exit(1)

    print(spec)

    for q in range(1, spec["numberOfQuestions"] + 1):
        for v in range(1, spec["numberOfVersions"] + 1):
            print("Reverting question {} version {}".format(q, v))
            try:
                startReverting(q, v)
            except Exception as e:
                print("Error reverting q.v {}.{} = {}".format(q, v, e))
                exit(1)

    try:
        messenger.closeUser()
        messenger.stop()
    except Exception as e:
        print("Closing down error = ", e)
        exit(1)

    exit(0)
