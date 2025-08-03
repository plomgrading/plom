# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018-2025 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2025 Philip D. Loewen

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from tqdm import tqdm

from plom.finish import with_finish_messenger
from plom.finish.coverPageBuilder import makeCover
from plom.finish.examReassembler import reassemble
from plom.question_labels import get_question_label


def download_data_build_cover_page(
    msgr, tmpdir: Path, t: int, maxMarks: dict, *, solution: bool = False
) -> Path:
    """Download information and create a cover page.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir: where to save the coverpage.
        t: Paper number.
        maxMarks: Maxmarks per question, dict str -> int.

    Keyword Args:
        solution: build coverpage for solutions, default False.
            In this case, ``qvm[2]`` is not used: not quite sure
            what is in there: probably same info but its ignored.

    Returns:
        Path and filename of the coverpage.
    """
    # should be [ [sid, sname], [q,v,m], [q,v,m], etc]
    cpi = msgr.RgetCoverPageInfo(t)
    spec = msgr.get_spec()
    sid = cpi[0][0]
    sname = cpi[0][1]
    # for each question, build [qlabel, ver, mark, maxPossibleMark]
    arg = []
    for qvm in cpi[1:]:
        question_label = get_question_label(spec, qvm[0])
        if solution:
            arg.append([question_label, qvm[1], maxMarks[str(qvm[0])]])
        else:
            arg.append([question_label, qvm[1], qvm[2], maxMarks[str(qvm[0])]])

    covername = tmpdir / f"cover_{int(t):04}.pdf"
    makeCover(
        arg,
        covername,
        paper_num=t,
        info=(sname, sid),
        solution=solution,
        exam_name=spec["longName"],
    )
    return covername


def _download_page_images(
    msgr, tmpdir: Path, num_questions: int, t: int | str, which: str
) -> list[dict[str, Any]]:
    """Download images for reassembling a particular paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir: directory to save the temp images.
        num_questions: number of questions.
        t: paper number.
        which: currently, can ``"id"`` or ``"dnm"``.

    Returns:
        The filenames of the marked page files as a list of dicts.
    """
    pagedata = msgr.get_pagedata(t)

    pages = []
    for row in pagedata:
        # Issue #2707: better use a image-type key
        if not row["pagename"].casefold().startswith(which):
            continue
        ext = Path(row["server_path"]).suffix
        filename = tmpdir / f'img_{int(t):04}_{row["pagename"]}{ext}'
        img_bytes = msgr.get_image(row["id"], row["md5"])
        with open(filename, "wb") as f:
            f.write(img_bytes)
        pages.append({"filename": filename, "rotation": row["orientation"]})
    return pages


def _download_annotation_images(
    msgr, tmpdir: Path, num_questions: int, t: int | str
) -> list:
    """Download images for reassembling a particular paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir: directory to save the temp images.
        num_questions: number of questions.
        t: paper number.

    Returns:
        The filenames of the marked page files.
    """
    marked_pages = []
    for q in range(1, num_questions + 1):
        annot_img_info, annot_img_bytes = msgr.get_annotations_image(t, q)
        im_type = annot_img_info["extension"]
        filename = tmpdir / f"img_{int(t):04}_q{q:02}.{im_type}"
        marked_pages.append(filename)
        with open(filename, "wb") as f:
            f.write(annot_img_bytes)

    return marked_pages


def _reassemble_one_paper(
    msgr,
    tmpdir: Path | str,
    outdir: Path,
    short_name: str,
    max_marks: dict,
    num_questions: int,
    t: int,
    sid: str | None,
    skip: bool,
) -> Path | None:
    """Reassemble a paper.

    Args:
        msgr (ManagerMessenger): Messenger object that talks to the server.
        tmpdir: The directory where we will download
            the annotated images for each question.
            We will also build cover pages there.
        outdir: where to build the reassembled pdf.
        short_name: the name of this exam, a form appropriate for
            a filename prefix, e.g., "math107mt1".
        max_marks: the maximum mark for each question, keyed by the
            question number, which seems to be a string.
        num_questions: how many questions did the assessment have?
        t: paper number.
        sid: The student number as a string.  Maybe `None` which
            means that student has no ID (?)  Currently we just skip these.
        skip: whether to skip existing pdf files.

    Returns:
        The full path of the reassembled pdf, or ``None`` if no pdf
        was made.  In this case, a warning or explanation will be printed.
    """
    if sid is None:
        # Note this is distinct from simply not yet ID'd
        print(f">>WARNING<< Paper {t} has an ID of 'None', not reassembling!")
        return None
    outname = outdir / f"{short_name}_{sid}.pdf"
    if skip and outname.exists():
        print(f"Skipping {outname}: already exists")
        return None
    tmpdir = Path(tmpdir)
    coverfile = download_data_build_cover_page(msgr, tmpdir, t, max_marks)
    id_pages = _download_page_images(msgr, tmpdir, num_questions, t, "id")
    dnm_pages = _download_page_images(msgr, tmpdir, num_questions, t, "dnm")
    marked_pages = _download_annotation_images(msgr, tmpdir, num_questions, t)
    reassemble(outname, short_name, sid, coverfile, id_pages, marked_pages, dnm_pages)
    return outname


@with_finish_messenger
def reassemble_paper(
    papernum: int,
    *,
    msgr,
    outdir: Path | str = Path("reassembled"),
    tmpdir: Path | str | None = None,
    skip: bool = False,
) -> Path | None:
    """Reassemble a particular paper.

    Args:
        papernum: which paper number to reassemble.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        outdir (pathlib.Path/str): where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        tmpdir: temporary space for download of
            images.  If you provide this, its your responsibility to
            clean it up.  The default is `None`, in which case we will
            use an OS temporary space and clean up afterward.
        skip: Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)

    Returns:
        The full path of the reassembled paper pdf, if one was created
        else None.

    Raises:
        ValueError: paper number does not exist, or is not ready.
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    spec = msgr.get_spec()
    short_name = spec["name"]
    num_questions = spec["numberOfQuestions"]
    max_marks = {str(q): msgr.getMaxMark(q) for q in range(1, num_questions + 1)}

    completedTests = msgr.RgetCompletionStatus()
    t = str(papernum)  # dicts keyed by strings
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
    # dict paper number -> [sid, sname]
    sid = identifiedTests[t][0]

    with tempfile.TemporaryDirectory() as _td:
        if tmpdir:
            # note in this case we don't use the _td temp dir
            # (and the files will not be deleted)
            print(f"Downloading temporary images to {tmpdir}")
            tmpdir = Path(tmpdir)
            tmpdir.mkdir(exist_ok=True)
        else:
            tmpdir = Path(_td)

        outname = _reassemble_one_paper(
            msgr,
            tmpdir,
            outdir,
            short_name,
            max_marks,
            num_questions,
            papernum,
            sid,
            skip,
        )
    return outname


@with_finish_messenger
def reassemble_all_papers(
    *,
    msgr,
    outdir: Path | str = Path("reassembled"),
    tmpdir: Path | str | None = None,
    skip: bool = False,
) -> None:
    """Reassemble all papers.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        outdir: where to save the reassembled pdf file
            Defaults to "reassembled/" in the current working directory.
            It will be created if it does not exist.
        tmpdir: temporary space for download of
            images.  If you provide this, its your responsibility to
            clean it up.  The default is `None`, in which case we will
            use an OS temporary space and clean up afterward.
        skip (bool): Default False, but if True, skip any pdf files
            we already have (Careful: without checking for changes!)
    """
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True)
    spec = msgr.get_spec()
    short_name = spec["name"]
    num_questions = spec["numberOfQuestions"]
    max_marks = {str(q): msgr.getMaxMark(q) for q in range(1, num_questions + 1)}

    completedTests = msgr.RgetCompletionStatus()
    # dict paper number -> [scanned, id'd, #q's marked]
    identifiedTests = msgr.getIdentified()
    # dict paper number -> [sid, sname]

    # This should be a conditional context manager, which can be done
    # using contextlib.ExitStack, but I found the result hard to read.
    with tempfile.TemporaryDirectory() as _td:
        if tmpdir:
            # note in this case we don't use the _td temp dir
            # (and the files will not be deleted)
            print(f"Downloading temporary images to {tmpdir}")
            tmpdir = Path(tmpdir)
            tmpdir.mkdir(exist_ok=True)
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
