# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import getpass

from plom.misc_utils import format_int_list_with_runs
from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException


def proc_everything(comps, numberOfQuestions):
    idList = []
    mList = [0 for j in range(numberOfQuestions + 1)]
    sList = [[] for j in range(numberOfQuestions + 1)]
    cList = []
    for t, v in comps.items():
        if v[0]:
            idList.append(int(t))
        mList[v[1]] += 1
        sList[v[1]].append(t)
        if v[0] and v[1] == numberOfQuestions:
            cList.append(t)
    idList.sort(key=int)
    # TODO bit crude, better to get from server
    numScanned = sum(mList)
    return idList, mList, sList, cList, numScanned


def print_everything(comps, numPapersProduced, numQ):
    idList, mList, sList, cList, numScanned = proc_everything(comps, numQ)
    print("*********************")
    print("** Completion data **")
    print("Produced papers: {}".format(numPapersProduced))
    if numPapersProduced == numScanned:
        print("Scanned papers: {}".format(numScanned))
    else:
        print("Scanned papers: {} (currently)".format(numScanned))
    print("Completed papers: {}".format(format_int_list_with_runs(cList)))
    print("Identified papers: {}".format(format_int_list_with_runs(idList)))
    for n in range(numQ + 1):
        print(
            "Number of papers with {} questions marked = {}. Tests numbers = {}".format(
                n, mList[n], format_int_list_with_runs(sList[n])
            )
        )


def print_still_out(outToDo):
    if len(outToDo) == 0:
        print("*******************************")
        print('** No tasks currently "out" ***')
        return
    print("*********************")
    print("** Tasks still out **")
    for x in outToDo:
        print("[{}, {}, {}]".format(x[0], x[1], x[2]))


def main(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    if not password:
        password = getpass.getpass("Please enter the 'manager' password:")

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorization run `plom-finish clear`."
        )
        exit(-1)

    spec = msgr.get_spec()
    max_papers = spec["numberToProduce"]
    numberOfQuestions = spec["numberOfQuestions"]
    completions = msgr.RgetCompletionStatus()
    outToDo = msgr.RgetOutToDo()

    msgr.closeUser()
    msgr.stop()

    print_everything(completions, max_papers, numberOfQuestions)

    idList, mList, sList, cList, numScanned = proc_everything(
        completions, numberOfQuestions
    )
    numberComplete = len(cList)
    print("{} of {} complete".format(numberComplete, numScanned))

    print_still_out(outToDo)

    if numberComplete == numScanned:
        exit(0)
    elif numberComplete < numScanned:
        exit(numScanned - numberComplete)
    else:
        print("Something terrible has happened")
        exit(-42)


if __name__ == "__main__":
    main()
