# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from collections import defaultdict
import glob
import os

from plom.rules import isValidStudentNumber
from plom.scan import with_scanner_messenger


def IDQorIDorBad(fullfname):
    """Factor filename into one of two forms or answer name is bad.

    Args:
        fullfname (str, Pathlib): a filename that is supposed to have
            a particular form.

    Returns:
        list: first entry is either "IDQ" or "JID" or "BAD", with other
            entries following in the "IDQ" and "JID" cases.
    """
    fname = os.path.basename(fullfname)
    splut = fname.split(".")
    try:
        QFlag = splut[-2].isnumeric() or splut[-2] == "_"
        IDFlag = isValidStudentNumber(splut[-3])
    except IndexError:
        return ["BAD"]
    if QFlag and IDFlag:  # [-3] is ID and [-2] is Q.
        return ["IDQ", splut[-3], splut[-2]]  # ID and Q
    elif isValidStudentNumber(splut[-2]):  # [-2] is ID
        return ["JID", splut[-2]]  # Just ID
    else:
        return ["BAD"]  # Bad format


def whoSubmittedWhatOnDisc():
    print(">> Checking submissions in local 'submittedHWByQ' subdirectory <<")
    hwByQ = defaultdict(list)
    problemFQ = []
    problemOF = []

    for fn in glob.glob(os.path.join("submittedHWByQ", "*.pdf")):
        IDQ = IDQorIDorBad(fn)
        if len(IDQ) == 3:
            sid, q = IDQ[1:]
            hwByQ[sid].append([fn, q])
        else:
            # print("File {} has incorrect format for homework-by-question".format(fn))
            problemFQ.append(os.path.basename(fn))

    for sid in sorted(hwByQ.keys()):
        print("#{} submitted q's {}".format(sid, sorted([x[1] for x in hwByQ[sid]])))

    if len(problemFQ) > 0:
        print(">>> Warning <<<")
        print(
            "These files in submittedHWByQ have the wrong name format: {}".format(
                problemFQ
            )
        )
        print("Please check them before proceeding. They will not be processed.")
    if len(problemOF) > 0:
        print(">>> Warning <<<")
        print(
            "These files in submittedHWExtra have the wrong name format: {}".format(
                problemOF
            )
        )
        print("Please check them before proceeding. They will not be processed.")


@with_scanner_messenger
def whoSubmittedWhatOnServer(*, msgr):
    # passes back dict {t: [sid, missing1, missing2, etc]}
    missingHWQ = msgr.getMissingHW()
    # passes back list of pairs [test_number, sid]
    completeHW = msgr.getCompleteHW()

    print(">> Checking hw submissions on server <<")
    print("The following students have complete submissions (each question present)")
    print(", ".join(sorted([x[1] for x in completeHW])))
    print()
    print(
        "The following students have incomplete submissions (missing questions indicated)"
    )
    for t, val in missingHWQ.items():
        print(f"\t{val[0]} is missing {val[1:]}")


@with_scanner_messenger
def print_who_submitted_what(directory_check=False, *, msgr):
    """Prints lists of HW and other submissions on server and/or local.

    * Prints list of hw-submissions already uploaded to server
    * Prints list of what hw-submissions are in the current submittedHWByQ directory
    * Prints list of what loose-submissions are in the current submittedLoose directory
    """
    if directory_check:
        whoSubmittedWhatOnDisc()
    else:
        whoSubmittedWhatOnServer(msgr=msgr)


# TODO: dead code, no callers?
@with_scanner_messenger
def verifiedComplete(*, msgr):
    spec = msgr.get_spec()
    numberOfQuestions = spec["numberOfQuestions"]

    hwByQ = defaultdict(list)
    for fn in glob.glob("submittedHWByQ/*.pdf"):
        IDQ = IDQorIDorBad(fn)
        if len(IDQ) == 3:
            sid, q = IDQ[1:]
            hwByQ[sid].append([fn, q])
    # return fileNames belonging to complete homeworks
    validFiles = []
    for sid in hwByQ:
        if len(hwByQ[sid]) == numberOfQuestions:
            validFiles += [x[0] for x in hwByQ[sid]]
    return validFiles
