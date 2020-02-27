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

from .testReassembler import reassemble
import plom.finishMessenger as finishMessenger
from plom.plom_exceptions import *

numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def reassembleTestCMD(shortName, outDir, t, sid):
    fnames = finishMessenger.RgetOriginalFiles(t)
    if len(fnames) == 0:
        # TODO: what is supposed to happen here?
        return
    rnames = ["../newServer/" + fn for fn in fnames]
    outname = os.path.join(outDir, "{}_{}.pdf".format(shortName, sid))
    #reassemble(outname, shortName, sid, None, rnames)
    return (outname, shortName, sid, None, rnames)


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(
        description="Returns list of tests that have been completed. No arguments = run as normal."
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
        finishMessenger.startMessenger(s, port=p)
    else:
        finishMessenger.startMessenger(args.server)

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
        finishMessenger.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run the 029_clearManagerLogin.py script."
        )
        exit(0)

    shortName = finishMessenger.getInfoShortName()
    # spec = finishMessenger.getInfoGeneral()
    # numberOfTests = spec["numberOfTests"]
    # numberOfQuestions = spec["numberOfQuestions"]

    outDir = "reassembled_ID_but_not_marked"
    os.makedirs(outDir, exist_ok=True)

    identifiedTests = finishMessenger.RgetIdentified()
    pagelists = []
    for t in identifiedTests:
        if identifiedTests[t][0] is not None:
            dat = reassembleTestCMD(shortName, outDir, t, identifiedTests[t][0])
            pagelists.append(dat)
        else:
            print(">>WARNING<< Test {} has no ID".format(t))

    finishMessenger.closeUser()
    finishMessenger.stopMessenger()

    def _f(y):
        reassemble(*y)

    with Pool() as p:
        r = list(
            tqdm(
                p.imap_unordered(_f, pagelists),
                total=len(pagelists),
            )
        )

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )
