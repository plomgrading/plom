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


def whoDidWhat():
    from plom.scan.hwSubmissionsCheck import whoSubmittedWhat

    whoSubmittedWhat()


def make_required_directories():
    # we need
    directory_list = [
        "archivedPDFs/submittedHWByQ",
        "archivedPDFs/submittedHWLoose",
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

    # trim down file_name - replace "submittedHWLoose/fname" with "fname", but pass appropriate flag
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


def uploadHWImages(server, password, unknowns=False, collisions=False):
    from plom.scan import sendPagesToServer

    # make directories for upload
    os.makedirs("sentPages/submittedHWByQ", exist_ok=True)
    os.makedirs("sentPages/submittedHWExtra", exist_ok=True)

    print("Upload hw images to server")
    [SIDQ, SIDO] = sendPagesToServer.uploadHWPages(server, password)
    print(
        "Homework (by Q) was uploaded to the following studentIDs: {}".format(
            SIDQ.keys()
        )
    )
    print(
        "Homework (extra) was uploaded to the following studentIDs: {}".format(
            SIDO.keys()
        )
    )


parser = argparse.ArgumentParser()
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command", description="Tools for dealing with scans.")
#
spW = sub.add_parser(
    "submitted",
    help="Get a list of SID and questions submitted in the submittedHomework directory.",
)
spP = sub.add_parser("process", help="Process scanned PDFs to images.")
spU = sub.add_parser("upload", help="Upload page images to scanner")
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser(
    "clear",
    help="Clear 'scanner' login",
    description="Clear 'scanner' login after a crash or other expected event.",
)
#


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


for x in (spP, spU, spS, spC):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if args.command == "submitted":
        whoDidWhat()
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
    # elif args.command == "upload":
    #     uploadHWImages(args.server, args.password)
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
