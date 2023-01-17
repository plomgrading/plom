# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018-2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import imghdr
from pathlib import Path
import tempfile

from tqdm import tqdm

from plom import get_question_label
from plom.finish import with_finish_messenger
from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble
from plom.plom_exceptions import PlomSeriousException


def download_data_build_cover_page(msgr, tmpdir, t, maxMarks, solution=False):
    """Download information and create a cover page.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path.str): where to save the coverpage.
        t (int): Test number.
        maxMarks (dict): Maxmarks per question str -> int.

    Keyword Args:
        solution (bool): build coverpage for solutions.

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
    makeCover(int(t), sname, sid, arg, covername, solution=solution)
    return covername


def download_page_images(msgr, tmpdir, num_questions, t, sid):
    """Download the images for reassembling a particular paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path): directory to save the temp images.
        num_questions (int): number of questions.
        t (str/int): Test number.
        sid (str): student number.

    Returns:
       tuple: (id_page_files, marked_page_files, dnm_page_files)
    """
    # empty list if no ID-page (return None) - eg for hw.
    id_pages = []
    id_image_blob = msgr.request_ID_image(t)
    if id_image_blob:
        # TODO: imghdr is deprecated
        im_type = imghdr.what(None, h=id_image_blob)
        id_page = tmpdir / f"img_{int(t):04}_id0.{im_type}"
        if not im_type:
            raise PlomSeriousException(f"Could not identify image type: {id_page}")
        with open(id_page, "wb") as f:
            f.write(id_image_blob)
        id_pages = [id_page]
    marked_pages = []
    for q in range(1, num_questions + 1):
        obj = msgr.get_annotations_image(t, q)
        # TODO: imghdr is deprecated
        im_type = imghdr.what(None, h=obj)
        filename = tmpdir / f"img_{int(t):04}_q{q:02}.{im_type}"
        if not im_type:
            raise PlomSeriousException(f"Could not identify image type: {filename}")
        marked_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    dnm_image_blobs = msgr.request_donotmark_images(t)
    dnm_pages = []
    for i, obj in enumerate(dnm_image_blobs):
        im_type = imghdr.what(None, h=obj)
        filename = tmpdir / f"img_{int(t):04}_dnm{i:02}.{im_type}"
        if not im_type:
            raise PlomSeriousException(f"Could not identify image type: {filename}")
        dnm_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(obj)
    # return id-page inside a list since then the 3 different page types
    # are returned consistently inside lists.
    return (id_pages, marked_pages, dnm_pages)


def _reassemble_one_paper(
    msgr, tmpdir, outdir, short_name, max_marks, num_questions, t, sid, skip
):
    """Reassemble a test paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir (pathlib.Path/str): The directory where we will download
            the annotated images for each question.
            We will also build cover pages there.
        outdir (pathlib.Path/str): where to build the reassembled pdf.
        short_name (str): the name of this exam, a form appropriate for
            a filename prefix, e.g., "math107mt1".
        max_marks (dict): the maximum mark for each question, keyed by the
            question number, which seems to be a string.
        t (int): Test number.
        sid (str/None): The student number as a string.  Maybe `None` which
            means that student has no ID (?)  Currently we just skip these.
        skip (bool): whether to skip existing pdf files.

    Returns:
        outname (pathlib.Path): the full path of the reassembled test pdf.
    """
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
    return outname


@with_finish_messenger
def reassemble_paper(
    testnum, *, msgr, outdir=Path("reassembled"), tmpdir=None, skip=False
):
    """Reassemble a particular test paper.

    Args:
        testnum (int): which test number to reassemble.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        tmpdir (pathlib.Path/str/None): temporary space for download of
            images.  If you provide this, its your responsibility to
            clean it up.  The default is `None`, in which case we will
            use an OS temporary space and clean up afterward.
        skip (bool): Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)

    Returns:
        pathlib.Path: the full path of the reassembled test pdf.

    Raises:
        ValueError: paper number does not exist, or is not ready.
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    short_name = msgr.getInfoShortName()
    spec = msgr.get_spec()
    num_questions = spec["numberOfQuestions"]
    max_marks = msgr.MgetAllMax()

    completedTests = msgr.RgetCompletionStatus()
    t = str(testnum)  # dicts keyed by strings
    try:
        completed = completedTests[t]
        # is 4-tuple [Scanned, IDed, #Marked, Last_update_time]
    except KeyError:
        raise ValueError(f"Paper {t} does not exist or is not marked") from None
    if not completed[0]:
        raise ValueError(f"Paper {t} is not completed: not scanned")
    if not completed[1]:
        raise ValueError(f"Paper {t} is not completed: not identified")
    if completed[2] != num_questions:
        raise ValueError(f"Paper {t} is not complete: unmarked questions")

    identifiedTests = msgr.getIdentified()
    # dict testNumber -> [sid, sname]
    sid = identifiedTests[t][0]

    with tempfile.TemporaryDirectory() as _td:
        if tmpdir:
            # note in this case we don't use the _td temp dir
            print(f"Downloading temporary images to {tmpdir}")
            tmpdir = Path(tmpdir)
        else:
            tmpdir = Path(_td)

        outname = _reassemble_one_paper(
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
    return outname


@with_finish_messenger
def reassemble_all_papers(*, msgr, outdir=Path("reassembled"), tmpdir=None, skip=False):
    """Reassemble all test papers.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        tmpdir (pathlib.Path/str/None): temporary space for download of
            images.  If you provide this, its your responsibility to
            clean it up.  The default is `None`, in which case we will
            use an OS temporary space and clean up afterward.
        skip (bool): Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    short_name = msgr.getInfoShortName()
    spec = msgr.get_spec()
    num_questions = spec["numberOfQuestions"]
    max_marks = msgr.MgetAllMax()

    completedTests = msgr.RgetCompletionStatus()
    # dict testnumber -> [scanned, id'd, #q's marked]
    identifiedTests = msgr.getIdentified()
    # dict testNumber -> [sid, sname]

    with tempfile.TemporaryDirectory() as _td:
        if tmpdir:
            # note in this case we don't use the _td temp dir
            print(f"Downloading temporary images to {tmpdir}")
            tmpdir = Path(tmpdir)
        else:
            tmpdir = Path(_td)

        for t, completed in tqdm(completedTests.items()):
            if completed[0] and completed[1] and completed[2] == num_questions:
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
