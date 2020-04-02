# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import getpass
import sys

from plom.misc_utils import format_int_list_with_runs
from plom.messenger import FinishMessenger
from plom.plom_exceptions import *

numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def proc_everything(comps):
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
    # TODO bit crude, better to get from server
    numScanned = sum(mList)
    return idList, tList, mList, sList, cList, numScanned


def print_everything(comps, numPapersProduced):
    idList, tList, mList, sList, cList, numScanned = proc_everything(comps)
    print("*********************")
    print("** Completion data **")
    print("Produced papers: {}".format(numPapersProduced))
    print("Scanned papers: {} (currently)".format(numScanned))
    print("Completed papers: {}".format(format_int_list_with_runs(cList)))
    print("Identified papers: {}".format(format_int_list_with_runs(idList)))
    print("Totalled papers: {}".format(format_int_list_with_runs(tList)))
    for n in range(numberOfQuestions + 1):
        print(
            "Number of papers with {} questions marked = {}. Tests numbers = {}".format(
                n, mList[n], format_int_list_with_runs(sList[n])
            )
        )


def main(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    if not password:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run `plom-finish clear`."
        )
        exit(-1)

    spec = msgr.getInfoGeneral()
    numberOfTests = spec["numberOfTests"]
    numberOfQuestions = spec["numberOfQuestions"]
    completions = msgr.RgetCompletions()
    msgr.closeUser()
    msgr.stop()

    print_everything(completions, numberOfTests)

    idList, tList, mList, sList, cList, numScanned = proc_everything(completions)
    numberComplete = len(cList)
    print("{} of {} complete".format(numberComplete, numScanned))
    if numberComplete == numScanned:
        exit(0)
    elif numberComplete < numScanned:
        exit(numScanned - numberComplete)
    else:
        print("Something terrible has happened")
        exit(-42)


if __name__ == "__main__":
    main()
