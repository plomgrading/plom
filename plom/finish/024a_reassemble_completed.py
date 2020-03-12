#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import getpass
import os
import shlex
import subprocess
from multiprocessing import Pool
from tqdm import tqdm

from .coverPageBuilder import makeCover
from .testReassembler import reassemble

from plom.messenger import FinishMessenger
from plom.plom_exceptions import *

numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def buildCoverPage(msgr, shortName, outDir, t, maxMarks):
    # should be [ [sid, sname], [q,v,m], [q,v,m] etc]
    cpi = msgr.RgetCoverPageInfo(t)
    sid = cpi[0][0]
    sname = cpi[0][1]
    # for each Q [q, v, mark, maxPossibleMark]
    arg = []
    for qvm in cpi[1:]:
        # append quads of [q,v,m,Max]
        arg.append([qvm[0], qvm[1], qvm[2], maxMarks[str(qvm[0])]])
    return (int(t), sname, sid, arg)
    # makeCover(int(t), sname, sid, arg)


def reassembleTestCMD(msgr, shortName, outDir, t, sid):
    fnames = msgr.RgetAnnotatedFiles(t)
    if len(fnames) == 0:
        # TODO: what is supposed to happen here?
        return
    covername = "coverPages/cover_{}.pdf".format(str(t).zfill(4))
    rnames = fnames
    outname = os.path.join(outDir, "{}_{}.pdf".format(shortName, sid))
    return (outname, shortName, sid, covername, rnames)
    # reassemble(outname, shortName, sid, covername, rnames)


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(
        description="Reassemble PDF files for fully-graded papers."
    )
    parser.add_argument("-w", "--password", type=str)
    parser.add_argument(
        "-s",
        "--server",
        metavar="SERVER[:PORT]",
        action="store",
        help="Which server to contact.",
    )
    args = parser.parse_args()
    if args.server and ":" in args.server:
        s, p = args.server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(args.server)
    msgr.start()

    # get the password if not specified
    if args.password is None:
        try:
            pwd = getpass.getpass("Please enter the 'manager' password:")
        except Exception as error:
            print("ERROR", error)
    else:
        pwd = args.password

    # get started
    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 029_clearManagerLogin.py script."
        )
        exit(0)

    shortName = msgr.getInfoShortName()
    spec = msgr.getInfoGeneral()
    numberOfTests = spec["numberOfTests"]
    numberOfQuestions = spec["numberOfQuestions"]

    outDir = "reassembled"
    os.makedirs("coverPages", exist_ok=True)
    os.makedirs(outDir, exist_ok=True)

    completedTests = msgr.RgetCompletions()
    # dict key = testnumber, then list id'd, tot'd, #q's marked
    identifiedTests = msgr.RgetIdentified()
    # dict key = testNumber, then pairs [sid, sname]
    maxMarks = msgr.MgetAllMax()

    # get data for cover pages and reassembly
    pagelists = []
    coverpagelist = []
    if True:
        for t in completedTests:
            if (
                completedTests[t][0] == True
                and completedTests[t][2] == numberOfQuestions
            ):
                if identifiedTests[t][0] is not None:
                    dat1 = buildCoverPage(msgr, shortName, outDir, t, maxMarks)
                    dat2 = reassembleTestCMD(
                        msgr, shortName, outDir, t, identifiedTests[t][0]
                    )
                    coverpagelist.append(dat1)
                    pagelists.append(dat2)
                else:
                    print(">>WARNING<< Test {} has no ID".format(t))

    msgr.closeUser()
    msgr.stop()

    def f(z):
        x, y = z
        if x and y:
            makeCover(*x)
            reassemble(*y)

    with Pool() as p:
        r = list(
            tqdm(
                p.imap_unordered(f, list(zip(coverpagelist, pagelists))),
                total=len(coverpagelist),
            )
        )
    # Serial
    # for z in zip(coverpagelist, pagelists):
    #    f(z)

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )
