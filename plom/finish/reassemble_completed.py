# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import os
from pathlib import Path
import shutil
import tempfile

from tqdm import tqdm

from plom import get_question_label
from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble


def download_data_build_cover_page(msgr, tmpdir, t, maxMarks):
    """Download information and create a cover page.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path.str): where to save the coverpage.
        t (int): Test number.
        maxMarks (dict): Maxmarks per question str -> int.

    Returns:
        pathlib.Path: filename of the coverpage.
    """
    # should be [ [sid, sname], [q,v,m], [q,v,m] etc]
    cpi = msgr.RgetCoverPageInfo(t)
    spec = msgr.get_spec()
    sid = cpi[0][0]
    sname = cpi[0][1]
    # for each Q [qlabel, ver, mark, maxPossibleMark]
    arg = []
    for qvm in cpi[1:]:
        question_label = get_question_label(spec, qvm[0])
        arg.append([question_label, qvm[1], qvm[2], maxMarks[str(qvm[0])]])
    testnumstr = str(t).zfill(4)
    covername = tmpdir / "cover_{}.pdf".format(testnumstr)
    makeCover(int(t), sname, sid, arg, covername)
    return covername


def download_page_images(msgr, tmpdir, num_questions, t, sid):
    """Download the images for reassembling a particular paper.

    Args:
        msgr (FinishMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path): directory to save the temp images.
        num_questions (int): number of questions.
        t (str/int): Test number.
        sid (str): student number.

    Returns:
       tuple: (id_page_files, marked_page_files, dnm_page_files)
    """
    id_image_blobs = msgr.request_ID_images(t)
    id_pages = []
    for i, obj in enumerate(id_image_blobs):
        filename = tmpdir / f"img_{int(t):04}_id{i:02}.png"
        id_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    marked_pages = []
    for q in range(1, num_questions + 1):
        obj = msgr.get_annotations_image(t, q)
        # Hardcoded to PNG here (and elsewhere!)
        filename = tmpdir / f"img_{int(t):04}_q{q:02}.png"
        marked_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    dnm_image_blobs = msgr.request_donotmark_images(t)
    dnm_pages = []
    for i, obj in enumerate(dnm_image_blobs):
        filename = tmpdir / f"img_{int(t):04}_dnm{i:02}.png"
        dnm_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    return (id_pages, marked_pages, dnm_pages)


def _reassemble_one_paper(
    msgr, tmpdir, outdir, short_name, max_marks, num_questions, t, sid, skip
):
    """Reassemble a test paper."""
    if sid is None:
        # Note this is distinct from simply not yet ID'd
        print(f">>WARNING<< Test {t} has an ID of 'None', not reassembling!")
        return
    outname = outdir / f"{short_name}_{sid}.pdf"
    if skip and outname.exists():
        print(f"Skipping {outname}: already exists")
        return
    coverfile = download_data_build_cover_page(msgr, tmpdir, t, max_marks)
    file_lists = download_page_images(msgr, tmpdir, num_questions, t, sid)
    reassemble(outname, short_name, sid, coverfile, *file_lists)


def start_messenger(server=None, pwd=None):
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
    return msgr


def reassemble_one_paper(
    testnum, server=None, pwd=None, outdir=Path("reassembled"), skip=False
):
    """Reassemble a test paper.

    Args:
        testnum (int): which test number would be reassembled.
        server (str)
        pwd (str)

    Keyword Args:
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        skip_existing (bool): Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)

    Raises:
        ValueError: does not exist, or not ready.
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    msgr = start_messenger(server, pwd)
    try:
        short_name = msgr.getInfoShortName()
        spec = msgr.get_spec()
        num_questions = spec["numberOfQuestions"]
        max_marks = msgr.MgetAllMax()

        completedTests = msgr.RgetCompletionStatus()
        t = str(testnum)  # dicts keyed by strings
        try:
            completed = completedTests[t]
        except KeyError:
            raise ValueError(f"Paper {t} does not exist or is not marked") from None
        if not completed[0]:
            raise ValueError(f"Paper {t} is not completed: not identified")
        if completed[1] != num_questions:
            raise ValueError(f"Paper {t} is not complete: unmarked questions")

        identifiedTests = msgr.RgetIdentified()
        # dict testNumber -> [sid, sname]
        sid = identifiedTests[t][0]
        # TODO: will a context manager delete content too? helpful here!
        tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))
        _reassemble_one_paper(
            msgr,
            tmpdir,
            outdir,
            short_name,
            max_marks,
            num_questions,
            testnum,
            sid,
            skip,
        )
        shutil.rmtree(tmpdir)
    finally:
        msgr.closeUser()
        msgr.stop()


def reassemble_all_papers(
    server=None, pwd=None, outdir=Path("reassembled"), skip=False
):
    """Reassemble all test papers.

    Args:
        server (str)
        pwd (str)

    Keyword Args:
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        skip (bool): Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    msgr = start_messenger(server, pwd)
    try:
        short_name = msgr.getInfoShortName()
        spec = msgr.get_spec()
        num_questions = spec["numberOfQuestions"]
        max_marks = msgr.MgetAllMax()

        completedTests = msgr.RgetCompletionStatus()
        # dict testnumber -> [id'd, #q's marked]
        identifiedTests = msgr.RgetIdentified()
        # dict testNumber -> [sid, sname]

        tmpdir = Path(tempfile.mkdtemp(prefix="tmp_images_", dir=os.getcwd()))
        print(f"Downloading to temp directory {tmpdir}")

        for t, completed in tqdm(completedTests.items()):
            if completed[0] and completed[1] == num_questions:
                sid = identifiedTests[t][0]
                _reassemble_one_paper(
                    msgr,
                    tmpdir,
                    outdir,
                    short_name,
                    max_marks,
                    num_questions,
                    t,
                    sid,
                    skip,
                )
        shutil.rmtree(tmpdir)
    finally:
        msgr.closeUser()
        msgr.stop()


def main(testnum, server, password, skip):
    if testnum == None:
        reassemble_all_papers(server, password, skip=skip)
    else:
        reassemble_one_paper(testnum, server, password, skip=skip)
