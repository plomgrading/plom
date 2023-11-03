# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Forest Kobayashi
# Copyright (C) 2022 Joey Shi

import sys
from textwrap import dedent

from plom.misc_utils import format_int_list_with_runs as with_runs
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
            mis-assigned an extra page to a test that is not actually in use.
            """
        )
    )


def print_classlist_db_xor(classlist, pns_to_ids, max_papers):
    """Find and print things in classlist or database (but not both)."""
    students_from_cl = {(s["id"], s["name"]) for s in classlist}
    students_from_db = {
        (s["sid"], s["sname"]) for n, s in pns_to_ids.items() if s["identified"]
    }

    cl_not_db = students_from_cl - students_from_db

    # db_not_cl = students_from_db - students_from_cl
    # Non-unique b/c of blanks, so instead of set subtraction above, we
    # compute, and stick the papernum in as well for unique triplets.
    db_not_cl = [
        (s["sid"], s["sname"], papernum)
        for papernum, s in pns_to_ids.items()
        if s["identified"] and (s["sid"], s["sname"]) not in students_from_cl
    ]
    # filter out those with None SID to highlight separately
    ided_to_None = []
    for papernum, v in pns_to_ids.items():
        if v["sid"] is None:
            # TODO: show sum of mark here?
            ided_to_None.append((v["sid"], v["sname"], papernum))

    if cl_not_db:
        print(
            f"There were {len(cl_not_db)} students listed in `classlist.csv` "
            "who do not seem to have submissions in the Plom database."
        )
        if len(classlist) > 1.1 * max_papers:
            # classlist too long, likely not useful info
            print(
                f"  (list omitted b/c only {max_papers} rows in the database"
                f" and {len(classlist)} in the classlist)"
            )
        else:
            for sid, sname in cl_not_db:
                print(f"  ID: {sid}\tName: {sname}")

    if db_not_cl:
        print(
            f"There were {len(db_not_cl)} students present in the Plom "
            "database who do not seem to be listed in `classlist.csv`."
        )
        for sid, sname, testnum in db_not_cl:
            print(f"  Test no.: {testnum}\tID: {sid}\tName: {sname}")

    if ided_to_None:
        print(f"There are {len(ided_to_None)} papers ID'd to SID None:")
        for sid, sname, papernum in ided_to_None:
            print(f"  Test no.: {papernum}\tID: {sid}\tName: {sname}")


def main(server=None, password=None, dangling_check=False):
    msgr = start_messenger(server, password)
    try:
        spec = msgr.get_spec()
        exam_info = msgr.get_exam_info()
        classlist = msgr.IDrequestClasslist()
        max_papers = exam_info["current_largest_paper_num"]
        numberOfQuestions = spec["numberOfQuestions"]
        completions = msgr.RgetCompletionStatus()
        outToDo = msgr.RgetOutToDo()
        dangling = msgr.getDanglingPages()
        paper_nums_to_ids = msgr.RgetSpreadsheet()
    finally:
        msgr.closeUser()
        msgr.stop()

    idList, hist, marked, completed, numScanned, partMarked = proc_everything(
        completions, numberOfQuestions
    )
    print("*********************")
    print("** Completion info **")
    print(f"Produced papers: {max_papers}")
    if max_papers == numScanned:
        print(f"Scanned papers: {numScanned}")
    else:
        print(f"Scanned papers: {numScanned} (currently)")
    print(f"Number of papers marked: {hist[numberOfQuestions]}")
    print(f"Number of papers identified: {len(idList)}")
    numberComplete = len(completed)
    print(f"Number completed (marked and ID'd): {numberComplete}")

    print("")
    print("******************************")
    print("** Detailed completion data **")
    print(f"Identified papers: {with_runs(idList)}")
    print(f"Completed papers (marked & ID'd): {with_runs(completed)}")
    print("Questions marked histogram:")
    pad = 1 if numberOfQuestions <= 9 else 2
    for n, h in enumerate(hist):
        print(f"{h:5} papers with {n:{pad}} questions marked: {with_runs(marked[n])}")
    print(
        f"{len(partMarked):5} papers have at least one question marked: {with_runs(partMarked)}"
    )

    print("")
    print_classlist_db_xor(classlist, paper_nums_to_ids, max_papers)

    print("")
    print_still_out(outToDo)
    print("")
    if dangling_check:
        print_dangling(dangling)
    else:
        print("************************************")
        print("** Dangling Pages check: disabled **")
        print("This is disabled by default, see command-line help")
        print()

    if len(partMarked) > numberComplete:
        s = "Warning: {} papers incomplete (part-marked or unidentified).".format(
            len(partMarked) - numberComplete
        )
        print("*" * len(s))
        print(s)
        print("*" * len(s))

    if numberComplete == numScanned:
        sys.exit(0)
    elif numberComplete < numScanned:
        sys.exit(numScanned - numberComplete)
    else:
        print("Something terrible has happened")
        sys.exit(-42)


if __name__ == "__main__":
    main()
