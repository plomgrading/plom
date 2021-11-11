# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

from multiprocessing import Pool
import os
from pathlib import Path
import shutil
import tempfile

from tqdm import tqdm

from plom import get_question_label
from plom.finish import start_messenger
from plom.finish.solutionAssembler import assemble
from plom.finish.reassemble_completed import download_data_build_cover_page


def checkAllSolutionsPresent(solutionList):
    # soln list = [ [q,v,md5sum], [q,v,""]]
    for X in solutionList:
        if X[2] == "":
            print("Missing solution to question {} version {}".format(X[0], X[1]))
            return False
    return True


def todo_build_assemble_args(msgr, srcdir, short_name, outdir, t):
    """Builds the information for assembling the solutions.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        srcdir (str): The directory we downloaded solns img to. Is also
            where cover page pdfs are stored
        short_name (str): name of the test without the student id.
        outdir (str): The directory we are putting the cover page in.
        t (int): Test number.

    Returns:
        list: appropriate solution files for this solution set.
    """
    info = msgr.RgetCoverPageInfo(t)
    # info is list of [[sid, sname], [q,v,m], [q,v,m]]
    sid = info[0][0]
    # make soln-file-List
    sfiles = []
    for X in info[1:]:
        sfiles.append(Path(srcdir) / f"solution.{X[0]}.{X[1]}.png")
    return sfiles


def _assemble_one_soln(msgr, tmpdir, outdir, short_name, max_marks, t, skip):
    """Assemble a solution."""
    outname = outdir / f"{short_name}_solutions_{sid}.pdf"
    if skip and outname.exists():
        print(f"Skipping {outname}: already exists")
        return
    coverfile = download_data_build_cover_page(msgr, tmpdir, t, max_marks)
    sfiles = todo_build_assemble_args(msgr, tmpdir, short_name, outdir, t)
    assemble(outname, short_name, sid, coverfile, sfiles)


def main(testnum=None, server=None, pwd=None):
    msgr = start_messenger(server, pwd)
    try:
        shortName = msgr.getInfoShortName()
        spec = msgr.get_spec()
        numberOfQuestions = spec["numberOfQuestions"]

        outdir = Path("solutions")
        outdir.mkdir(exist_ok=True)
        tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))

        solutionList = msgr.getSolutionStatus()
        if not checkAllSolutionsPresent(solutionList):
            raise RuntimeError("Problems getting solution images.")
        print("All solutions present.")
        print(f"Downloading solution images to temp directory {tmpdir}")
        for X in tqdm(solutionList):
            # triples [q,v,md5]
            img = msgr.getSolutionImage(X[0], X[1])
            filename = tmpdir / f"solution.{X[0]}.{X[1]}.png"
            with open(filename, "wb") as f:
                f.write(img)

        # dict key = testnumber, then list id'd, #q's marked
        completedTests = msgr.RgetCompletionStatus()
        maxMarks = msgr.MgetAllMax()

        if testnum is not None:
            t = str(testnum)
            try:
                completed = completedTests[t]
            except KeyError:
                raise ValueError(
                    f"Paper {t} does not exist or otherwise not ready"
                ) from None
            if not completed[0]:
                raise ValueError(f"Paper {t} not scanned, cannot reassemble")
            if not completed[1]:
                raise ValueError(f"Paper {t} not identified, cannot reassemble")
            if completed[2] == numberOfQuestions:
                print(f"Note: paper {t} not fully marked but building soln anyway")
            _assemble_one_soln(msgr, tmpdir, outdir, shortName, maxMarks, t, False)
        else:
            print(f"Building UP TO {len(completedTests)} solutions...")
            N = 0
            for t, completed in tqdm(completedTests.items()):
                # check if the given test is scanned and identified
                if not (completed[0] and completed[1]):
                    continue
                # Maybe someone wants only the finished papers?
                # if completed[2] != numberOfQuestions:
                #     continue
                _assemble_one_soln(msgr, tmpdir, outdir, shortName, maxMarks, t, False)
                N += 1
            print(f"Assembled {N} solutions from papers scanning and ID'd")
    finally:
        msgr.closeUser()
        msgr.stop()

    shutil.rmtree(tmpdir)
