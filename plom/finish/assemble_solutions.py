# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

from pathlib import Path
import tempfile

from tqdm import tqdm

from plom.finish import with_finish_messenger
from plom.finish.solutionAssembler import assemble
from plom.finish.reassemble_completed import download_data_build_cover_page


def _assemble_one_soln(
    msgr,
    tmpdir,
    outdir,
    short_name,
    max_marks,
    t,
    sid,
    watermark=False,
    verbose=True,
    *,
    skip=True,
):
    """Assemble a solution for one particular paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
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
        watermark (bool): whether to watermark solns with student-id.
        verbose (bool): print messages or not.

    Keyword Args:
        skip (bool): whether to skip existing pdf files.

    Returns:
        None
    """
    if sid is None:
        # Note this is distinct from simply not yet ID'd
        print(f">>WARNING<< Test {t} has an ID of 'None', not reassembling!")
        return
    outname = outdir / f"{short_name}_solutions_{sid}.pdf"
    if skip and outname.exists():
        if verbose:
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
    """Assessemble solution documents.

    Keyword Args:
        testnum (int): which test number to reassemble.
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        watermark (bool): whether to watermark solns with student-id.
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "solutions/" in the current working directory.
            It will be created if it does not exist.
        verbose (bool): print messages or not.
            Note: still prints in case of `None` for an student id.

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

    with tempfile.TemporaryDirectory() as _td:
        tmp = Path(_td)

        solutionList = msgr.getSolutionStatus()
        for q, v, md5 in solutionList:
            if md5 == "":
                raise RuntimeError(f"Missing solution to question {q} version {v}")
        if verbose:
            print("All solutions present.")
            print(f"Downloading solution images to temp directory {tmp}")
        for q, v, md5 in tqdm(solutionList):
            img = msgr.getSolutionImage(q, v)
            filename = tmp / f"solution.{q}.{v}.png"
            with open(filename, "wb") as f:
                f.write(img)

        completedTests = msgr.RgetCompletionStatus()
        # dict testnumber -> [scanned, id'd, #q's marked]
        identifiedTests = msgr.getIdentified()
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
                msgr, tmp, outdir, shortName, maxMarks, t, sid, watermark, verbose
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
                    msgr, tmp, outdir, shortName, maxMarks, t, sid, watermark, verbose
                )
                N += 1
            if verbose:
                print(f"Assembled {N} solutions from papers scanning and ID'd")
