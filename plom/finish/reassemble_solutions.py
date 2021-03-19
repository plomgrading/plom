# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

import getpass
import os
from pathlib import Path
from multiprocessing import Pool

from tqdm import tqdm

from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish.locationSpecCheck import locationAndSpecCheck
from .solutionReassembler import reassemble


numberOfQuestions = 0


def _parfcn(z):
    """Parallel function used below, must be defined in root of module.

    Args:
        z (tuple): Arguments to reassemble and makeCover.
    """
    x, y = z
    if x and y:
        makeCover(*x)
        reassemble(*y)


def checkAllSolutionsPresent(solutionList):
    # soln list = [ [q,v,md5sum], [q,v,""]]
    for X in solutionList:
        if X[2] == "":
            print("Missing solution to question {} version {}".format(X[0], X[1]))
            return False
    return True


def build_solutions(msgr, testNumber):
    cpi = msgr.RgetCoverPageInfo(testNumber)
    # cpi is list of [[sid, sname], [q,v,m], [q,v,m]]
    version_list = [X[1] for X in cpi[1:]]
    print("Soln for sid {} = images {}".format(cpi[0][0], version_list))
    return (testNumber, cpi[0], version_list)


def main(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    if not pwd:
        pwd = getpass.getpass('Please enter the "manager" password: ')

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorisation run `plom-finish clear`."
        )
        exit(1)

    shortName = msgr.getInfoShortName()
    spec = msgr.get_spec()
    numberOfQuestions = spec["numberOfQuestions"]
    if not locationAndSpecCheck(spec):
        print("Problems confirming location and specification. Exiting.")
        msgr.closeUser()
        msgr.stop()
        exit(1)

    outDir = "reassembled"
    os.makedirs("solutions", exist_ok=True)
    os.makedirs(outDir, exist_ok=True)

    solutionList = msgr.getSolutionStatus()
    if not checkAllSolutionsPresent(solutionList):
        print("Problems getting solution images. Exiting.")
        msgr.closeUser()
        msgr.stop()
        exit(1)

    print("All solutions present.")

    # dict key = testnumber, then list id'd, #q's marked
    completedTests = msgr.RgetCompletionStatus()
    for t in completedTests:
        # check if the given test is ready for reassembly (and hence soln ready for reassembly)
        if completedTests[t][0] == True and completedTests[t][1] == numberOfQuestions:
            build_solutions(msgr, t)

    msgr.closeUser()
    msgr.stop()


if __name__ == "__main__":
    main()
