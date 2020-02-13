#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later


import argparse
import getpass
import sys

# ----------------------
from misc_utils import format_int_list_with_runs
import finishMessenger
from plom_exceptions import *

numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def print_everything(comps):
    print("*********************")
    print("** Completion data **")
    idList = []
    tList = []
    mList = [0 for j in range(numberOfQuestions + 1)]
    sList = [[] for j in range(numberOfQuestions + 1)]
    cList = []
    for t, v in comps.items():
        if v[0]:
            idList.append(int(t))
        if v[1]:
            tList.append(int(t))
        mList[v[2]] += 1
        sList[v[2]].append(t)
        if v[0] and v[1] and v[2] == numberOfQuestions:
            cList.append(t)
    idList.sort(key=int)
    tList.sort(key=int)
    print("Completed papers: {}".format(format_int_list_with_runs(cList)))
    print("Identified papers: {}".format(format_int_list_with_runs(idList)))
    print("Totalled papers: {}".format(format_int_list_with_runs(tList)))
    for n in range(numberOfQuestions + 1):
        print(
            "Number of papers with {} questions marked = {}. Tests numbers = {}".format(
                n, mList[n], format_int_list_with_runs(sList[n])
            )
        )


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(
        description="Returns list of tests that have been completed. No arguments = run as normal."
    )
    parser.add_argument("-w", "--password", type=str)
    parser.add_argument(
        "-s", "--server", help="Which server to contact (must specify port as well)."
    )
    parser.add_argument(
        "-p", "--port", help="Which port to use (must specify server as well)."
    )
    args = parser.parse_args()

    # must spec both server+port or neither.
    if args.server and args.port:
        finishMessenger.startMessenger(altServer=args.server, altPort=args.port)
    elif args.server is None and args.port is None:
        finishMessenger.startMessenger()
    else:
        print("You must specify both the server and the port. Quitting.")
        quit()

    # get the password if not specified
    if args.password is None:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = args.password

    # get started
    try:
        finishMessenger.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 029_clearManagerLogin.py script."
        )
        exit(0)

    spec = finishMessenger.getInfoGeneral()
    numberOfTests = spec["numberOfTests"]
    numberOfQuestions = spec["numberOfQuestions"]
    completions = finishMessenger.RgetCompletions()
    finishMessenger.closeUser()
    finishMessenger.stopMessenger()

    print_everything(completions)
