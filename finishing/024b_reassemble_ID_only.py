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

import finishMessenger
from plom_exceptions import *

numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def reassembleTestCMD(shortName, outDir, t, sid):
    fnames = finishMessenger.RgetOriginalFiles(t)
    if len(fnames) == 0:
        return
    rnames = ["../newServer/" + fn for fn in fnames]
    return 'python3 testReassembler.py {} {} {} "" "{}"\n'.format(
        shortName, sid, outDir, rnames
    )


if __name__ == "__main__":
    # get commandline args if needed
    parser = argparse.ArgumentParser(
        description="Returns list of tests that have been completed. No arguments = run as normal."
    )
    parser.add_argument("-w", "--password", type=str)
    parser.add_argument(
        "-s", "--server", help="Which server to contact (must specify port as well)."
    )
    parser.add_argument(
        "-p", "--port", help="Which port to use (must specify server as well)."
    )
    args = parser.parse_args()

    # must spec both server+port or neither.
    if args.server and args.port:
        finishMessenger.startMessenger(altServer=args.server, altPort=args.port)
    elif args.server is None and args.port is None:
        finishMessenger.startMessenger()
    else:
        print("You must specify both the server and the port. Quitting.")
        quit()

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
    try:
        os.mkdir(outDir)
    except FileExistsError:
        pass

    identifiedTests = finishMessenger.RgetIdentified()
    # Open a file for the list of commands to process to reassemble papers
    fh = open("./commandlist.txt", "w")
    for t in identifiedTests:
        if identifiedTests[t][0] is not None:
            fh.write(reassembleTestCMD(shortName, outDir, t, identifiedTests[t][0]))
        else:
            print(">>WARNING<< Test {} has no ID".format(t))
    fh.close()
    # pipe the commandlist into gnu-parallel
    cmd = shlex.split("parallel --bar -a commandlist.txt")
    subprocess.run(cmd, check=True)
    os.unlink("commandlist.txt")

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )
