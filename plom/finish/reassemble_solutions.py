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
    reassemble(*z)


def checkAllSolutionsPresent(solutionList):
    # soln list = [ [q,v,md5sum], [q,v,""]]
    for X in solutionList:
        if X[2] == "":
            print("Missing solution to question {} version {}".format(X[0], X[1]))
            return False
    return True


def build_reassemble_args(msgr, short_name, out_dir, t):
    """Builds the information for reassembling the entire test.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        short_name (str): name of the test without the student id.
        out_dir (str): The directory we are putting the cover page in.
        t (int): Test number.

    Returns:
       tuple : (outname, short_name, sid, covername, rnames)
    """
    info = msgr.RgetCoverPageInfo(t)
    # info is list of [[sid, sname], [q,v,m], [q,v,m]]
    sid = info[0][0]
    # make soln-file-List
    # solns are hard-coded solutionImages/solution.q.v.png
    sfiles = []
    for X in info[1:]:
        sfiles.append(
            os.path.join("solutionImages", "solution.{}.{}.png".format(X[0], X[1]))
        )

    out_dir = Path(out_dir)
    outname = out_dir / "{}_solutions_{}.pdf".format(short_name, sid)
    return (outname, short_name, sid, sfiles)


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

    outDir = "solutions"
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
    # arg-list for reassemble solutions
    solution_args = []
    for t in completedTests:
        # check if the given test is ready for reassembly (and hence soln ready for reassembly)
        if completedTests[t][0] == True and completedTests[t][1] == numberOfQuestions:
            # append args for this test to list
            solution_args.append(build_reassemble_args(msgr, shortName, outDir, t))

    msgr.closeUser()
    msgr.stop()

    N = len(solution_args)
    print("Reassembling {} papers...".format(N))
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(_parfcn, solution_args), total=N))
    # Serial
    # for z in solution_args
    #    _parfcn(z)


if __name__ == "__main__":
    main()
