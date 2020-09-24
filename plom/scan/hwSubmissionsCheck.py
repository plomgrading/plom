# -*- coding: utf-8 -*-

"""Check which students have submitted what in the submittedHWByQ and submittedHWExtra directories"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import glob
import getpass
import os

from plom.rules import isValidStudentNumber
from plom.messenger import ScanMessenger
from plom.plom_exceptions import *


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
    hwOne = defaultdict(list)
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

    for fn in glob.glob(os.path.join("submittedLoose", "*.pdf")):
        IDQ = IDQorIDorBad(fn)
        if len(IDQ) == 2:
            sid = IDQ[1]
            hwOne[sid].append(fn)
        else:
            # print("File {} has incorrect format for homework-by-question".format(fn))
            problemOF.append(os.path.basename(fn))

    for sid in sorted(hwByQ.keys()):
        print("#{} submitted q's {}".format(sid, sorted([x[1] for x in hwByQ[sid]])))

    for sid in sorted(hwOne.keys()):
        print("#{} submitted loose pages".format(sid))

    warn = []
    for sid in sorted(hwOne.keys()):
        if sid in hwByQ:
            warn.append(sid)
    if len(warn) > 0:
        print(">>> Warning <<<")
        print(
            "These students submitted both HW by Q, and HW in loose pages: {}".format(
                warn
            )
        )
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


def whoSubmittedWhatOnServer(server, password):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        exit(10)

    missingHWQ = msgr.getMissingHW()  # passes back dict
    completeHW = msgr.getCompleteHW()  # passes back list [test_number, sid]

    msgr.closeUser()
    msgr.stop()

    print(">> Checking incomplete submissions on server <<")
    print("The following students have complete submissions (each question present)")
    print(", ".join(sorted([x[1] for x in completeHW])))
    print(
        "The following students have incomplete submissions (missing questions indicated)"
    )
    for t in missingHWQ:
        print("{} missing {}".format(missingHWQ[t][1], missingHWQ[t][2:]))


def whoSubmittedWhat(server=None, password=None, directory_check=False):
    if directory_check:
        whoSubmittedWhatOnDisc()
    else:
        whoSubmittedWhatOnServer(server, password)


def verifiedComplete(server=None, password=None):

    if server and ":" in server:
        s, p = server.split(":")
        msgr = ScanMessenger(s, port=p)
    else:
        msgr = ScanMessenger(server)
    msgr.start()

    # get the password if not specified
    if password is None:
        try:
            pwd = getpass.getpass("Please enter the 'scanner' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = password

    # get started
    try:
        msgr.requestAndSaveToken("scanner", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-hwscan clear"'
        )
        exit(10)

    # grab number of questions - so we can work out what is missing
    spec = msgr.get_spec()
    numberOfQuestions = spec["numberOfQuestions"]

    msgr.closeUser()
    msgr.stop()

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
