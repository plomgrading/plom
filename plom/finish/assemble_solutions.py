# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
import shutil
import tempfile

from tqdm import tqdm

from plom.finish import with_finish_messenger
from plom.finish.solutionAssembler import assemble
from plom.finish.reassemble_completed import download_data_build_cover_page


def checkAllSolutionsPresent(solutionList):
    # soln list = [ [q,v,md5sum], [q,v,""]]
    for X in solutionList:
        if X[2] == "":
            print("Missing solution to question {} version {}".format(X[0], X[1]))
            return False
    return True


def _assemble_one_soln(
    msgr, tmpdir, outdir, short_name, max_marks, t, sid, skip, watermark=False
):
    """Assemble a solution for one particular paper.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path/str): The directory where we downloaded solns
            images.  We will also build cover pages there.
        outdir (pathlib.Path/str): where to build the solution pdf.
        short_name (str): the name of this exam, a form appropriate for
            a filename prefix, e.g., "math107mt1".
        max_marks (dict): the maximum mark for each question, keyed by the
            question number, which seems to be a string.
        t (int): Test number.
        sid (str/None): The student number as a string.  Maybe `None` which
            means that student has no ID (?)  Currently we just skip these.
        skip (bool): whether to skip existing pdf files.
        watermark (bool): whether to watermark solns with student-id.

    Returns:
        None
    """
    if sid is None:
        # Note this is distinct from simply not yet ID'd
        print(f">>WARNING<< Test {t} has an ID of 'None', not reassembling!")
        return
    outname = outdir / f"{short_name}_solutions_{sid}.pdf"
    if skip and outname.exists():
        print(f"Skipping {outname}: already exists")
        return
    coverfile = download_data_build_cover_page(
        msgr, tmpdir, t, max_marks, solution=True
    )

    info = msgr.RgetCoverPageInfo(t)
    # info is list of [[sid, sname], [q,v,m], [q,v,m]]
    soln_files = []
    for X in info[1:]:
        soln_files.append(Path(tmpdir) / f"solution.{X[0]}.{X[1]}.png")
    assemble(outname, short_name, sid, coverfile, soln_files, watermark)


@with_finish_messenger
def assemble_solutions(
    *, msgr, testnum=None, watermark=False, outdir=Path("solutions"), verbose=True
):
    """Assessemble solution document for a particular test paper.

    Keyword Args:
        testnum (int): which test number to reassemble.
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        watermark (bool): whether to watermark solns with student-id.
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "solutions/" in the current working directory.
            It will be created if it does not exist.
        verbose (bool): print messages or not.
            Note: still prints in many cases and probably also
            assumes a human reads that output: perhaps needs different
            error handling.

    Returns:
        None

    Raises:
        ValueError: paper number does not exist, or is not ready.
        RuntimeError: cannot get solution images.
    """
    shortName = msgr.getInfoShortName()
    spec = msgr.get_spec()
    numberOfQuestions = spec["numberOfQuestions"]

    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=Path.cwd()))

    solutionList = msgr.getSolutionStatus()
    if not checkAllSolutionsPresent(solutionList):
        raise RuntimeError("Problems getting solution images.")
    if verbose:
        print("All solutions present.")
        print(f"Downloading solution images to temp directory {tmpdir}")
    for X in tqdm(solutionList):
        # triples [q,v,md5]
        img = msgr.getSolutionImage(X[0], X[1])
        filename = tmpdir / f"solution.{X[0]}.{X[1]}.png"
        with open(filename, "wb") as f:
            f.write(img)

    completedTests = msgr.RgetCompletionStatus()
    # dict testnumber -> [scanned, id'd, #q's marked]
    identifiedTests = msgr.RgetIdentified()
    # dict testNumber -> [sid, sname]
    maxMarks = msgr.MgetAllMax()

    if testnum is not None:
        t = str(testnum)
        try:
            completed = completedTests[t]
            # is 4-tuple [Scanned, IDed, #Marked, Last_update_time]
        except KeyError:
            raise ValueError(
                f"Paper {t} does not exist or otherwise not ready"
            ) from None
        if not completed[0]:
            raise ValueError(f"Paper {t} not scanned, cannot reassemble")
        if not completed[1]:
            raise ValueError(f"Paper {t} not identified, cannot reassemble")
        if completed[2] != numberOfQuestions:
            if verbose:
                print(f"Note: paper {t} not fully marked but building soln anyway")
        sid = identifiedTests[t][0]
        _assemble_one_soln(
            msgr, tmpdir, outdir, shortName, maxMarks, t, sid, False, watermark
        )
    else:
        if verbose:
            print(f"Building UP TO {len(completedTests)} solutions...")
        N = 0
        for t, completed in tqdm(completedTests.items()):
            # check if the given test is scanned and identified
            if not (completed[0] and completed[1]):
                continue
            # Maybe someone wants only the finished papers?
            # if completed[2] != numberOfQuestions:
            #     continue
            sid = identifiedTests[t][0]
            _assemble_one_soln(
                msgr, tmpdir, outdir, shortName, maxMarks, t, sid, False, watermark
            )
            N += 1
        if verbose:
            print(f"Assembled {N} solutions from papers scanning and ID'd")

    shutil.rmtree(tmpdir)
