# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

from plom.misc_utils import format_int_list_with_runs
from plom.finish import start_messenger


def proc_everything(comps, numberOfQuestions):
    scannedList = []
    idList = []
    mList = [0 for j in range(numberOfQuestions + 1)]
    histList = [[] for j in range(numberOfQuestions + 1)]
    cList = []
    partMarked = []
    # each comps item = [Scanned, IDed, #Marked]
    for t, v in comps.items():
        if v[0]:
            scannedList.append(int(t))
        if v[1]:
            idList.append(int(t))
        if v[2] > 0:
            partMarked.append(int(t))

        mList[v[2]] += 1
        histList[v[2]].append(t)
        if v[0] and v[1] and v[2] == numberOfQuestions:
            cList.append(t)
    idList.sort(key=int)
    # TODO bit crude, better to get from server
    numScanned = len(scannedList)
    return idList, mList, histList, cList, numScanned, partMarked


def print_everything(comps, numPapersProduced, numQ):
    idList, mList, histList, cList, numScanned, partMarked = proc_everything(
        comps, numQ
    )
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
                n, mList[n], format_int_list_with_runs(histList[n])
            )
        )
    print(
        "Papers with at least one question marked = {}".format(
            format_int_list_with_runs(partMarked)
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


def print_dangling(dangling):
    if len(dangling) == 0:
        print("***********************")
        print('** No dangling pages **')
        return
    print("******************************")
    print("** WARNING - Dangling pages **")
    for x in dangling:
        if x['type'] == 'tpage':
            print(". tpage: t{} p{} of group {}".format(x['test'], x['page'], x['group']))
        else:
            print(". {}: t{} o{} of group {}]".format(x['type'], x['test'], x['order'], x['group']))


def main(server=None, password=None):
    msgr = start_messenger(server, password)
    try:
        spec = msgr.get_spec()
        max_papers = spec["numberToProduce"]
        numberOfQuestions = spec["numberOfQuestions"]
        completions = msgr.RgetCompletionStatus()
        outToDo = msgr.RgetOutToDo()
        dangling = msgr.RgetDanglingPages()
    finally:
        msgr.closeUser()
        msgr.stop()

    print_everything(completions, max_papers, numberOfQuestions)

    idList, mList, sList, cList, numScanned, partMarked = proc_everything(
        completions, numberOfQuestions
    )
    numberComplete = len(cList)
    print("{} complete of {} scanned".format(numberComplete, numScanned))

    print_still_out(outToDo)
    print_dangling(dangling)

    if len(partMarked) > numberComplete:
        print("*********************")
        print(
            "Still {} part-marked papers to go.".format(
                len(partMarked) - numberComplete
            )
        )
        print("*********************")

    if numberComplete == numScanned:
        exit(0)
    elif numberComplete < numScanned:
        exit(numScanned - numberComplete)
    else:
        print("Something terrible has happened")
        exit(-42)


if __name__ == "__main__":
    main()
