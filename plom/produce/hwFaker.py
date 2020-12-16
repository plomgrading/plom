# -*- coding: utf-8 -*-

"""Plom tools for scribbling fake answers on PDF files"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import csv
import os
import random
from pathlib import Path
from glob import glob

from getpass import getpass
import json
import base64
import fitz

from . import paperdir as _paperdir
from plom import __version__
from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException

from .faketools import possible_answers as possibleAns


def makeHWLoose(numberOfQuestions, paperNumber, studentID, studentName, prefix):
    # pick one or two questions to "do" with one or 2 pages.
    didA = random.randint(1, 1 + numberOfQuestions)
    didB = random.randint(1, 1 + numberOfQuestions)
    if random.random() < 0.5 or didA == didB:
        doneQ = [didA]
    else:
        doneQ = [didA, didB]

    fname = Path("submittedLoose") / "{}.{}.pdf".format(prefix, studentID)
    doc = fitz.open()

    for q in doneQ:
        # construct pages
        for pn in range(random.randint(1, 2)):
            page = doc.newPage(-1, 612, 792)  # put page at end
            if pn == 0:  # put name and student number on start of Q
                rect1 = fitz.Rect(20, 24, 400, 54)
                rc = page.insertTextbox(
                    rect1,
                    "LPage for Q.{} -".format(q) + studentName + ":" + studentID,
                    fontsize=14,
                    color=[0.1, 0.1, 0.1],
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                assert rc > 0
            else:  # just put Question
                rect1 = fitz.Rect(20, 24, 400, 54)
                rc = page.insertTextbox(
                    rect1,
                    "LPage for Q.{} -".format(q),
                    fontsize=14,
                    color=[0.1, 0.1, 0.1],
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                assert rc > 0
            rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            text = random.choice(possibleAns)
            rc = page.insertTextbox(
                rect,
                text,
                fontsize=13,
                color=[0.1, 0.1, 0.8],
                fontname="helv",
                fontfile=None,
                align=0,
            )
            assert rc > 0

    doc.save(fname)


def makeFakeHW(
    numberOfQuestions, paperNumber, studentID, studentName, prefix, maximum_pages
):
    did = random.randint(
        numberOfQuestions - 1, numberOfQuestions
    )  # some subset of questions.
    doneQ = sorted(random.sample(list(range(1, 1 + numberOfQuestions)), did))
    for q in doneQ:
        fname = Path("submittedHWByQ") / "{}.{}.{}.pdf".format(prefix, studentID, q)
        doc = fitz.open()
        scribble_doc(doc, studentID, studentName, maximum_pages, q)
        doc.save(fname)


def makeFakeHW2(
    numberOfQuestions, paperNumber, studentID, studentName, prefix, maximum_pages
):
    did = random.randint(
        numberOfQuestions - 1, numberOfQuestions
    )  # some subset of questions.
    doneQ = sorted(random.sample(list(range(1, 1 + numberOfQuestions)), did))
    fname = Path("submittedHWByQ") / "{}.{}.{}.pdf".format(prefix, studentID, "_")
    doc = fitz.open()
    for q in doneQ:
        scribble_doc(doc, studentID, studentName, maximum_pages, q)
    doc.save(fname)


def scribble_doc(doc, studentID, studentName, maximum_pages, q):
    if True:
        # construct pages
        for pn in range(random.randint(1, maximum_pages)):
            page = doc.newPage(-1, 612, 792)  # page at end
            if pn == 0:
                # put name and student number on p1 of the Question
                rect1 = fitz.Rect(20, 24, 300, 44)
                rc = page.insertTextbox(
                    rect1,
                    "Q.{} -".format(q) + studentName + ":" + studentID,
                    fontsize=14,
                    color=[0.1, 0.1, 0.1],
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                assert rc > 0

            rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            text = random.choice(possibleAns)
            rc = page.insertTextbox(
                rect,
                text,
                fontsize=13,
                color=[0.1, 0.1, 0.8],
                fontname="helv",
                fontfile=None,
                align=0,
            )
            assert rc > 0


def download_classlist_and_spec(server=None, password=None):
    """Download list of student IDs/names and test specification from server."""
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    if not password:
        password = getpass('Please enter the "manager" password: ')

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another management tool running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-build clear"'
        )
        exit(10)
    try:
        classlist = msgr.IDrequestClasslist()
    except PlomBenignException as e:
        print("Failed to download classlist: {}".format(e))
        exit(4)
    try:
        spec = msgr.get_spec()
    except PlomBenignException as e:
        print("Failed to get specification: {}".format(e))
        exit(4)

    msgr.closeUser()
    msgr.stop()
    return classlist, spec


def main():
    """Main function used for running.

    1. Generates the files.
    2. Creates the fake data filled pdfs using fill_in_fake_data_on_exams.
    3. Generates second batch for first half of papers.
    4. Generates loose pages for two students - currently unused.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    parser.add_argument("-w", "--password", type=str, help='for the "manager" user')
    args = parser.parse_args()

    # grab classlist
    classlist, spec = download_classlist_and_spec(args.server, args.password)

    # get number named
    numberNamed = spec["numberToName"]
    numberOfQuestions = spec["numberOfQuestions"]
    # the named papers come from the first few lines of classlist
    sid = {}
    k = 0
    for row in classlist:
        sid[k] = [row[0], row[1]]
        k += 1
        if k >= numberNamed:
            break

    os.makedirs("submittedHWByQ", exist_ok=True)
    os.makedirs("submittedLoose", exist_ok=True)

    print("NumberNamed = {}".format(numberNamed))

    num_all_q_one_bundle = 2
    prefixes = ["hwA", "hwB"]  # we'll make two batches one bigger than other.
    for prefix in prefixes:
        if prefix == "hwA":
            for k in range(numberNamed - num_all_q_one_bundle):
                makeFakeHW(numberOfQuestions, k, sid[k][0], sid[k][1], prefix, 3)
        else:
            for k in range(numberNamed // 2):  # fewer in second batch
                makeFakeHW(numberOfQuestions, k, sid[k][0], sid[k][1], prefix, 1)

        # give a few loose pages to the first two students in both batches
        for k in range(5):
            makeHWLoose(numberOfQuestions, k, sid[k][0], sid[k][1], prefix)

    # a few more for "all questions in one" bundling
    for k in range(numberNamed - num_all_q_one_bundle, numberNamed):
        makeFakeHW2(numberOfQuestions, k, sid[k][0], sid[k][1], "semiloose", 3)


if __name__ == "__main__":
    main()
