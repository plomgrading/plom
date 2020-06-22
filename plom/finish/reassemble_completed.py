# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
import os
import shlex
import subprocess
from multiprocessing import Pool
from tqdm import tqdm

from .coverPageBuilder import makeCover
from .examReassembler import reassemble

from plom.messenger import FinishMessenger
from plom.plom_exceptions import *
from plom.finish.locationSpecCheck import locationAndSpecCheck

numberOfQuestions = 0


# parallel function used below, must be defined in root of module
def parfcn(z):
    x, y = z
    if x and y:
        makeCover(*x)
        reassemble(*y)


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
    os.makedirs("coverPages", exist_ok=True)
    os.makedirs(outDir, exist_ok=True)

    completedTests = msgr.RgetCompletionStatus()
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

    N = len(coverpagelist)
    print("Reassembling {} papers...".format(N))
    with Pool() as p:
        r = list(
            tqdm(p.imap_unordered(parfcn, list(zip(coverpagelist, pagelists))), total=N)
        )
    # Serial
    # for z in zip(coverpagelist, pagelists):
    #    parfcn(z)

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )


if __name__ == "__main__":
    main()
