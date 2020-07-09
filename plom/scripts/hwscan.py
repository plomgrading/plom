#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning homework and pushing to servers."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
from collections import defaultdict
import glob
import os
import shutil

from plom import __version__
from plom.rules import isValidStudentNumber


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def IDQorIDorBad(fullfname):
    fname = os.path.basename(fullfname)
    splut = fname.split(".")
    QFlag = splut[-2].isnumeric()
    IDFlag = isValidStudentNumber(splut[-3])
    if QFlag and IDFlag:  # [-3] is ID and [-2] is Q.
        return ["IDQ", splut[-3], splut[-2]]  # ID and Q
    elif isValidStudentNumber(splut[-2]):  # [-2] is ID
        return ["JID", splut[-2]]  # Just ID
    else:
        return ["BAD"]  # Bad format


def whoDidWhat(server, password, directory_check):
    from plom.scan.hwSubmissionsCheck import whoSubmittedWhat

    whoSubmittedWhat(server, password, directory_check)


def make_required_directories():
    # we need
    directory_list = [
        "archivedPDFs/submittedHWByQ",
        "archivedPDFs/submittedLoose",
        "bundles",
        "uploads/sentPages",
        "uploads/discardedPages",
        "uploads/collidingPages",
        "uploads/sentPages/unknowns",
        "uploads/sentPages/collisions",
    ]
    for dir in directory_list:
        os.makedirs(dir, exist_ok=True)


def processLooseScans(server, password, file_name, student_id):
    make_required_directories()
    from plom.scan.hwSubmissionsCheck import IDQorIDorBad
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer

    # trim down file_name - replace "submittedLoose/fname" with "fname", but pass appropriate flag
    short_name = os.path.split(file_name)[1]
    IDQ = IDQorIDorBad(short_name)
    if len(IDQ) != 2:  # should return [JID, sid]
        print("File name has wrong format. Should be 'blah.sid.pdf'. Stopping.")
        return
    sid = IDQ[1]
    if sid != student_id:
        print(
            "Student ID supplied {} does not match that in filename {}. Stopping.".format(
                student_id, sid
            )
        )
        return
    print(
        "Process and upload file {} as loose pages for sid {}".format(
            short_name, student_id
        )
    )
    bundle_name = sendPagesToServer.declareBundle(file_name, server, password)
    # pass as list since processScans expects a list.
    scansToImages.processScans([short_name], hwLoose=True)
    # send the images to the server
    sendPagesToServer.uploadLPages(bundle_name, student_id, server, password)


def processHWScans(server, password, file_name, student_id, question_list):
    make_required_directories()
    from plom.scan.hwSubmissionsCheck import IDQorIDorBad
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer

    question = int(question_list[0])  # args passes '[q]' rather than just 'q'

    # do sanity checks on file_name
    # trim down file_name - replace "submittedHWByQ/fname" with "fname", but pass appropriate flag
    short_name = os.path.split(file_name)[1]
    IDQ = IDQorIDorBad(short_name)
    if len(IDQ) != 3:  # should return [IDQ, sid, q]
        print("File name has wrong format - should be 'blah.sid.q.pdf'. Stopping.")
        return
    sid, q = IDQ[1:]
    if sid != student_id:
        print(
            "Student ID supplied {} does not match that in filename {}. Stopping.".format(
                student_id, sid
            )
        )
        return
    if int(q) != question:
        print(
            "Question supplied {} does not match that in filename {}. Stopping.".format(
                question, q
            )
        )
        return
    print(
        "Process and upload file {} as answer to question {} for sid {}".format(
            short_name, question, student_id
        )
    )
    bundle_name = sendPagesToServer.declareBundle(file_name, server, password)
    # pass as list since processScans expects a list.
    scansToImages.processScans([short_name], hwByQ=True)
    # send the images to the server
    sendPagesToServer.uploadHWPages(bundle_name, student_id, question, server, password)


def processAllHWByQ(server, password, yes_flag):
    from plom.scan.hwSubmissionsCheck import IDQorIDorBad

    submissions = defaultdict(list)
    for file_name in sorted(glob.glob(os.path.join("submittedHWByQ", "*.pdf"))):
        IDQ = IDQorIDorBad(file_name)
        if len(IDQ) == 3:
            sid, q = IDQ[1:]
            submissions[sid].append([q, file_name])

    print("Submission summary: ")
    for sid in submissions:
        sub_list = sorted([int(x[0]) for x in submissions[sid]])
        print_list = []
        for q in range(sub_list[0], sub_list[-1] + 1):
            n = sub_list.count(q)
            if n == 0:
                continue
            elif n == 1:
                print_list.append("{}".format(q))
            else:
                print_list.append("{}(x{})".format(q, n))
        print("# {}: {}".format(sid, print_list))

    if yes_flag:
        print("Processing and uploading all of the above submissions.")
    elif input("Process and upload all of the above submissions? [y/n]") != "y":
        print("Stopping.")
        return
    for sid in submissions:
        print("Processing id {}:".format(sid))
        for question, file_name in submissions[sid]:
            processHWScans(server, password, file_name, sid, question)


def processMissing(server, password, yes_flag):
    from plom.scan import checkScanStatus

    missingHWQ = checkScanStatus.checkMissingHWQ(server, password)
    # returns list for each test [scanned-tpages-present boolean, sid, missing-question-numbers]
    reallyMissing = {}  # new list of those without tpages present
    for t in missingHWQ:
        if missingHWQ[t][0]:  # scanned test-pages present, so no replacing.
            print(
                "Student {}'s paper has tpages present, so skipping".format(
                    missingHWQ[t][1]
                )
            )
        else:
            print(
                "Student {} is missing questions {}".format(
                    missingHWQ[t][1], missingHWQ[t][2:]
                )
            )
            reallyMissing[t] = missingHWQ[t]

    if len(reallyMissing) == 0:
        print("All papers either complete or have scanned test-pages present.")
        return

    if yes_flag:
        print("Replacing all missing questions with 'did not submit' pages.")
    elif input("Replace all missing with 'did not submit' pages? [y/n]") != "y":
        print("Stopping.")
        return

    for t in reallyMissing:
        sid = reallyMissing[t][1]
        for q in reallyMissing[t][2:]:
            print("Replacing q{} of sid {}".format(q, sid))
            checkScanStatus.replaceMissingHWQ(server, password, sid, q)


parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command", description="Tools for dealing with scans.")
#
spW = sub.add_parser(
    "submitted",
    help="status of student-submitted work, either local or on server",
    description="List student IDs and their submitted questions in the local"
    + " 'submittedHWByQ' directory or their work already uploaded the server.",
)
spP = sub.add_parser(
    "process", help="Process indicated PDFs for one student and upload to server."
)
spA = sub.add_parser(
    "allbyq",
    help="Process and upload all PDFs in 'submittedHWByQ' directory and upload to server",
)
spM = sub.add_parser(
    "missing", help="Replace missing answers with 'not submitted' pages.",
)
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser(
    "clear",
    help="Clear 'scanner' login",
    description="Clear 'scanner' login after a crash or other expected event.",
)
#

spW.add_argument(
    "-d",
    "--directory",
    action="store_true",
    help="Check submissions in local directory and not on server.",
)

spP.add_argument("hwPDF", action="store", help="PDF containing homework")
spP.add_argument("studentid", action="store", help="Student ID")
spPql = spP.add_mutually_exclusive_group(required=True)
spPql.add_argument(
    "-l",
    "--loose",
    action="store_true",
    help="Whether or not to upload file as loose pages.",
)
spPql.add_argument(
    "-q",
    "--question",
    nargs=1,
    action="store",
    help="Which question is answered in file.",
)

spA.add_argument(
    "-y", "--yes", action="store_true", help="Answer yes to prompts.",
)
spM.add_argument(
    "-y", "--yes", action="store_true", help="Answer yes to prompts.",
)


for x in (spW, spP, spA, spS, spC, spM):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "submitted":
        whoDidWhat(args.server, args.password, args.directory)
    elif args.command == "process":
        if args.loose:
            processLooseScans(
                args.server, args.password, args.hwPDF, args.studentid,
            )
        else:
            processHWScans(
                args.server, args.password, args.hwPDF, args.studentid, args.question,
            )
            # argparse makes args.question a list.
    elif args.command == "allbyq":
        processAllHWByQ(args.server, args.password, args.yes)
    elif args.command == "missing":
        processMissing(args.server, args.password, args.yes)
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()
        print("\n>> Processing and uploading homework <<")
        print(">>>> WRITE DOCS <<<<")

    exit(0)


if __name__ == "__main__":
    main()
