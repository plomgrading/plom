# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

from multiprocessing import Pool
import os
from pathlib import Path
import shutil
import tempfile

from tqdm import tqdm

from plom import get_question_label
from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish.solutionAssembler import assemble
from plom.finish.coverPageBuilder import makeCover


numberOfQuestions = 0


def _parfcn(z):
    """Parallel function used below, must be defined in root of module.

    Args:
        z (tuple): Arguments to assemble and makeSolnCover.
    """
    x, y = z
    if x and y:
        makeCover(*x, solution=True)
        assemble(*y)


def checkAllSolutionsPresent(solutionList):
    # soln list = [ [q,v,md5sum], [q,v,""]]
    for X in solutionList:
        if X[2] == "":
            print("Missing solution to question {} version {}".format(X[0], X[1]))
            return False
    return True


def build_soln_cover_data(msgr, tmpdir, t, maxMarks):
    """Builds the information used to create solution cover pages.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        t (int): Test number.
        maxMarks (dict): Maxmarks per question str -> int.

    Returns:
        tuple: (testnumber, sname, sid, tab) where `tab` is a table with
            rows `[q_label, ver, mark, max_mark]`.
    """
    # should be [ [sid, sname], [q,v,m], [q,v,m] etc]
    cpi = msgr.RgetCoverPageInfo(t)
    spec = msgr.get_spec()
    sid = cpi[0][0]
    sname = cpi[0][1]
    # for each Q [q, v, mark, maxPossibleMark]
    arg = []
    for qvm in cpi[1:]:
        question_label = get_question_label(spec, qvm[0])
        arg.append([question_label, qvm[1], qvm[2], maxMarks[str(qvm[0])]])
    testnumstr = str(t).zfill(4)
    covername = tmpdir / "cover_{}.pdf".format(testnumstr)
    return (int(t), sname, sid, arg, covername)


def build_assemble_args(msgr, srcdir, short_name, outdir, t):
    """Builds the information for assembling the solutions.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        srcdir (str): The directory we downloaded solns img to. Is also
            where cover page pdfs are stored
        short_name (str): name of the test without the student id.
        outdir (str): The directory we are putting the cover page in.
        t (int): Test number.

    Returns:
       tuple : (outname, short_name, sid, covername, rnames)
    """
    info = msgr.RgetCoverPageInfo(t)
    # info is list of [[sid, sname], [q,v,m], [q,v,m]]
    sid = info[0][0]
    # make soln-file-List
    sfiles = []
    for X in info[1:]:
        sfiles.append(Path(srcdir) / f"solution.{X[0]}.{X[1]}.png")

    outdir = Path(outdir)
    outname = outdir / f"{short_name}_solutions_{sid}.pdf"
    testnumstr = str(t).zfill(4)
    covername = srcdir / f"cover_{testnumstr}.pdf"
    return (outname, short_name, sid, covername, sfiles)


def main(server=None, pwd=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

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
        raise

    try:
        shortName = msgr.getInfoShortName()
        spec = msgr.get_spec()
        numberOfQuestions = spec["numberOfQuestions"]

        outdir = Path("solutions")
        outdir.mkdir(exist_ok=True)
        tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))
        print(f"Downloading to temp directory {tmpdir}")

        solutionList = msgr.getSolutionStatus()
        if not checkAllSolutionsPresent(solutionList):
            raise RuntimeError("Problems getting solution images.")
        print("All solutions present.")
        print("Downloading solution images to temp directory {}".format(tmpdir))
        for X in solutionList:
            # triples [q,v,md5]
            img = msgr.getSolutionImage(X[0], X[1])
            filename = tmpdir / f"solution.{X[0]}.{X[1]}.png"
            with open(filename, "wb") as f:
                f.write(img)

        # dict key = testnumber, then list id'd, #q's marked
        completedTests = msgr.RgetCompletionStatus()
        maxMarks = msgr.MgetAllMax()
        # arg-list for assemble solutions
        solution_args = []
        # get data for cover pages
        cover_args = []
        for t in completedTests:
            # check if the given test is ready for reassembly (and hence soln ready for assembly)
            if (
                completedTests[t][0] == True
                and completedTests[t][1] == numberOfQuestions
            ):
                # append args for this test to list
                cover_args.append(build_soln_cover_data(msgr, tmpdir, t, maxMarks))
                solution_args.append(
                    build_assemble_args(msgr, tmpdir, shortName, outdir, t)
                )
    finally:
        msgr.closeUser()
        msgr.stop()

    N = len(solution_args)
    print("Assembling {} solutions...".format(N))
    with Pool() as p:
        r = list(
            tqdm(
                p.imap_unordered(_parfcn, list(zip(cover_args, solution_args))), total=N
            )
        )

    # Serial
    # for z in zip(cover_args, solution_args)
    #    _parfcn(z)

    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
