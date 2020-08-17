# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

import getpass
import os
from multiprocessing import Pool
from tqdm import tqdm

from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish.locationSpecCheck import locationAndSpecCheck
from .examReassembler import reassemble


numberOfTests = 0
numberOfQuestions = 0


def _parfcn(y):
    """Parallel function used below, must be defined in root of module. Reassemble a pdf from the cover and question images.

    Leave coverfname as None to omit it (e.g., when totalling).

    Args:
        y : arguments to testReassembler.reassemble
    """
    reassemble(*y)


def reassemble_test_CMD(msgr, short_name, outDir, t, sid):
    """Reassembles a test with a filename that includes the directory and student id.

    Args:
        msgr (FinishMessenger): the messenger to the plom server.
        short_name (str): the name of the test.
        outDir (str): the directory the reassembled test will exist in.
        t (int): test number.
        sid (str): student id.

    Returns:
        tuple (outname, short_name, sid, None, rnames): descriptions below.
        outname (str): the full name of the file.
        short_name (str): same as argument.
        sid (str): sane as argument.
        rnames (str): the real file name.
    """
    fnames = msgr.RgetOriginalFiles(t)
    if len(fnames) == 0:
        # TODO: what is supposed to happen here?
        return
    rnames = fnames
    outname = os.path.join(outDir, "{}_{}.pdf".format(short_name, sid))
    # reassemble(outname, short_name, sid, None, rnames)
    return (outname, short_name, sid, None, rnames)


def main(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    if not pwd:
        pwd = getpass.getpass("Please enter the 'manager' password: ")

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorization run `plom-finish clear`."
        )
        exit(1)

    shortName = msgr.getInfoShortName()
    spec = msgr.get_spec()

    if not locationAndSpecCheck(spec):
        print("Problems confirming location and specification. Exiting.")
        msgr.closeUser()
        msgr.stop()
        exit(1)

    outDir = "reassembled_ID_but_not_marked"
    os.makedirs(outDir, exist_ok=True)

    identifiedTests = msgr.RgetIdentified()
    pagelists = []
    for t in identifiedTests:
        if identifiedTests[t][0] is not None:
            dat = reassemble_test_CMD(msgr, shortName, outDir, t, identifiedTests[t][0])
            pagelists.append(dat)
        else:
            print(">>WARNING<< Test {} has no ID".format(t))

    msgr.closeUser()
    msgr.stop()

    N = len(pagelists)
    print("Reassembling {} papers...".format(N))
    with Pool() as p:
        r = list(tqdm(p.imap_unordered(_parfcn, pagelists), total=N))

    print(">>> Warning <<<")
    print(
        "This still gets files by looking into server directory. In future this should be done over http."
    )


if __name__ == "__main__":
    main()
