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
from .testReassembler import reassemble

from plom.messenger import FinishMessenger
from plom.plom_exceptions import *
from plom.finish.locationSpecCheck import locationAndSpecCheck

numberOfTests = 0
numberOfQuestions = 0


def _parfcn(z):
    """Parallel function used below, must be defined in root of module

    Args:
        z (tuple): Arguments to reassemble and makeCover, of the form (x, y).
    
    x:
        test_num (int): the test number for the test wea re making the cover for. 
        sname (str): student name.
        sid (str): student id.
        tab (list): information about the test that should be put on the coverpage.

    y:
        out_name (str): name of the file we are assembling.
        short_name (str): name of the file without the whole directory. 
        sid (str): the student id.
        cover_fname (str): the name of the file of the coverpage of this test.
        img_list (str): the groupimage files  

    """
    x, y = z
    if x and y:
        makeCover(*x)
        reassemble(*y)


def build_cover_page(msgr, outDir, t, maxMarks):
    """Builds the information used to create cover pages.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        outDir (str): The directory we are putting the cover page in.
        t (int): Test number.
        maxMarks (dict): Maxmarks per question str -> int.

    Returns:
        tuple : (testnumber, sname, sid, arg).
        testnumber (int): testnumber of the coverpage that has been built.
        sname (str): student name.
        sid (str): student id.
        arg (tuple): quads of the form [q, v, mark, maxPossibleMark]
    """
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


def reassemble_test_CMD(msgr, short_name, out_dir, test_num, student_id):
    """Builds the information for reassembling the entire test.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        short_name (str): name of the test without the student id.
        out_dir (str): The directory we are putting the cover page in.
        test_num (int): Test number.
        student_id (str): student number.

    Returns:
       tuple : (outname, short_name, sid, covername, rnames)
    """
    fnames = msgr.RgetAnnotatedFiles(test_num)
    if len(fnames) == 0:
        # TODO: what is supposed to happen here?
        return
    covername = "coverPages/cover_{}.pdf".format(str(test_num).zfill(4))
    rnames = fnames
    outname = os.path.join(out_dir, "{}_{}.pdf".format(short_name, student_id))
    return (outname, short_name, student_id, covername, rnames)


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
    spec = msgr.getInfoGeneral()
    numberOfTests = spec["numberOfTests"]
    numberOfQuestions = spec["numberOfQuestions"]
    if not locationAndSpecCheck(spec):
        print("Problems confirming location and specification. Exiting.")
        msgr.closeUser()
        msgr.stop()
        exit(1)

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
                    dat1 = build_cover_page(msgr, outDir, t, maxMarks)
                    dat2 = reassemble_test_CMD(
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
            tqdm(
                p.imap_unordered(_parfcn, list(zip(coverpagelist, pagelists))), total=N
            )
        )

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )


if __name__ == "__main__":
    main()
