# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Forest Kobayashi
# Copyright (C) 2022 Joey Shi

import sys
from textwrap import dedent

from plom.misc_utils import format_int_list_with_runs
from plom.finish import start_messenger


def proc_everything(comps, numberOfQuestions):
    scannedList = []
    idList = []
    mList = [0 for j in range(numberOfQuestions + 1)]  # marked
    histList = [[] for j in range(numberOfQuestions + 1)]  # test numbers
    cList = []  # completed
    partMarked = []
    # each comps item = [Scanned, IDed, #Marked, Last_update_time]
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
        print("** No dangling pages **")
        return
    print("******************************")
    print("** WARNING - Dangling pages **")
    for x in dangling:
        if x["type"] == "tpage":
            print(
                ". tpage: t{} p{} of group {}".format(x["test"], x["page"], x["group"])
            )
        else:
            print(
                ". {}: t{} o{} of group {}]".format(
                    x["type"], x["test"], x["order"], x["group"]
                )
            )
    print(
        dedent(
            """
            A dangling page is part of a test that is not yet completely scanned
            and uploaded.  If you have assigned all extra pages etc and there
            are still dangling pages, then this might indicates that you have
            mis-assigned an extra page to a test that has not actually in use.
            """
        )
    )


def print_classlist_db_xor(classlist, pns_to_ids, max_papers):
    """Find and print things in classlist or database (but not both)."""

    # Note: note all rows of pns_to_ids are identified: does this matter?

    students_from_cl = {(s["id"], s["name"]) for s in classlist}
    students_from_db = {(s["sid"], s["sname"]) for n, s in pns_to_ids.items()}
    students_to_papernum = {(s["sid"], s["sname"]): n for n, s in pns_to_ids.items()}

    cl_not_db = students_from_cl - students_from_db
    db_not_cl = students_from_db - students_from_cl

    if cl_not_db:
        print(
            f"There were {len(cl_not_db)} students listed in `classlist.csv` "
            "who do not seem to have submissions in the Plom database."
        )
        # classlist too long, than this is not useful info
        if len(classlist) > max_papers:
            print(f"  (omitted list b/c only {max_papers} entries in the database)")
        else:
            for sid, sname in cl_not_db:
                print(f"  ID: {sid}\tName: {sname}")

    if db_not_cl:
        print(
            f"There were {len(db_not_cl)} students present in the Plom "
            "database who do not seem to be listed in `classlist.csv`."
        )
        for s in db_not_cl:
            try:
                testnum = students_to_papernum[s]
            except KeyError:
                print(f"WARNING: could not find testnum for {s}!")
                print("Continuing, but this is very likely a bug!")
            else:
                print(f"  Test no.: {testnum}\tID: {s[0]}\tName: {s[1]}")


def main(server=None, password=None):
    msgr = start_messenger(server, password)
    try:
        spec = msgr.get_spec()
        classlist = msgr.IDrequestClasslist()
        max_papers = spec["numberToProduce"]
        numberOfQuestions = spec["numberOfQuestions"]
        completions = msgr.RgetCompletionStatus()
        outToDo = msgr.RgetOutToDo()
        dangling = msgr.getDanglingPages()
        paper_nums_to_ids = msgr.RgetSpreadsheet()
    finally:
        msgr.closeUser()
        msgr.stop()

    print_everything(completions, max_papers, numberOfQuestions)

    idList, mList, sList, cList, numScanned, partMarked = proc_everything(
        completions, numberOfQuestions
    )
    numberComplete = len(cList)
    print("{} complete of {} scanned".format(numberComplete, numScanned))

    print_classlist_db_xor(classlist, paper_nums_to_ids, max_papers)

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
        sys.exit(0)
    elif numberComplete < numScanned:
        sys.exit(numScanned - numberComplete)
    else:
        print("Something terrible has happened")
        sys.exit(-42)


if __name__ == "__main__":
    main()
