# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Peter Lee

from __future__ import annotations

import csv
from multiprocessing import Pool
import os
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from plom.create import paperdir as paperdir_name
from plom.specVerifier import build_page_to_version_dict
from .mergeAndCodePages import make_PDF


def _make_PDF(x) -> None:
    """Call make_PDF from mergeAndCodePages with arguments expanded.

    *Note*: this is a little bit of glue to make the parallel Pool code
    elsewhere work.

    Arguments:
        x (tuple): this is expanded as the arguments to :func:`make_PDF`.
    """
    make_PDF(*x)


def outputProductionCSV(spec, make_PDF_args) -> None:
    """Output a csv with info on produced papers.

    Take the make_PDF_args that were used and dump them in a csv.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        make_PDF_args (list): a list of tuples of info for each paper
    """
    numberOfPages = spec["numberOfPages"]
    numberOfQuestions = spec["numberOfQuestions"]

    header = ["test_number", "sID", "sname"]
    for q in range(1, numberOfQuestions + 1):
        header.append("q{}.version".format(q))
    for p in range(1, numberOfPages + 1):
        header.append("p{}.version".format(p))
    # start writing to the csv
    with open("produced_papers.csv", "w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)
        for paper in make_PDF_args:
            # args = spec, paper_index, qv-map, student-info, other stuff
            # we need only a few bits of the tuple - paper_index, qvmap and student-info
            idx, qver, student_info = paper[1:4]
            # make page to version from the qvmap
            page_to_version = build_page_to_version_dict(spec, qver)
            # print the student info if there.
            if student_info:
                row = [idx, student_info["id"], student_info["name"]]
            else:  # just skip those columns
                row = [idx, None, None]
            for q in range(1, numberOfQuestions + 1):
                row.append(qver[q])
            for p in range(1, numberOfPages + 1):
                row.append(page_to_version[p])
            csv_writer.writerow(row)


def build_papers_backend(
    spec: dict[str, Any],
    global_question_version_map: dict[int, dict[int, int]],
    *,
    classlist_by_papernum: dict[int, dict[str, str]] = {},
    fakepdf: bool = False,
    no_qr: bool = False,
    indexToMake: int | None = None,
    xcoord: float | None = None,
    ycoord: float | None = None,
) -> None:
    """Builds the papers using _make_PDF, optionally prenamed.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        global_question_version_map (dict): dict of dicts mapping first by
            paper number (int) then by question number (int) to version (int).

    Keyword Arguments:
        classlist_by_papernum (dict): classlist keyed by ``papernum`` (int).
            Each value is a dicts with keys ``id`` and ``name``.  Any
            paper numbers corresponding to keys in `classlists_by_papernum`
            will be have names and IDs stamped on the front.  Can be an empty
            dict or omitted to not use this feature.
        fakepdf (bool): when true, the build empty pdfs (actually empty files)
            for use when students upload homework or similar (and only 1 version).
        no_qr (bool): when True, don't stamp with QR codes.  Default: False
            (which means *do* stamp with QR codes).
        indexToMake (int/None): specified paper number to be built.  If
            None then build all papers.  If this parameter is specified,
            only this paper will be built and the others will be ignored.
        xcoord (float): percentage from left to right of page to place
            ID/Signature box.
        ycoord (float): percentage from top to bottom of page to place
            ID/Signature box.

    Returns:
        None
    """
    # mapping from pages to groups for labelling top of pages
    make_PDF_args = []
    papersToMake: Iterable = []
    if indexToMake is None:
        papersToMake = range(1, spec["numberToProduce"] + 1)
    else:
        papersToMake = [indexToMake]
    for paper_index in papersToMake:
        question_version_map = global_question_version_map[paper_index]
        student_info = classlist_by_papernum.get(paper_index, None)
        make_PDF_args.append(
            (
                spec,
                paper_index,
                question_version_map,
                student_info,
                xcoord,
                ycoord,
                no_qr,
                fakepdf,
            )
        )

    if os.name == "nt":
        # Issue #2172, Pool/multiproc failing on Windows, use loop
        for x in tqdm(make_PDF_args):
            make_PDF(*x)  # type: ignore
    else:
        num_PDFs = len(make_PDF_args)
        with Pool() as pool:
            list(tqdm(pool.imap_unordered(_make_PDF, make_PDF_args), total=num_PDFs))
    # output CSV with all this info in it
    print("Writing produced_papers.csv.")
    outputProductionCSV(spec, make_PDF_args)


def check_pdf_and_prename_if_needed(
    spec: dict[str, Any],
    msgr,
    *,
    classlist_by_papernum: dict[int, dict[str, str]] = {},
    paperdir: Path | None = None,
    indexToCheck: int | None = None,
) -> None:
    """Check pdf(s) are present on disk and id papers that are prenamed.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        msgr (Messenger): an open active connection to the server.

    Keyword Arguments:
        classlist_by_papernum (dict): classlist keyed by ``papernum`` (int).
            Each value is a dicts with keys ``id`` and ``name``.  Any
            paper numbers corresponding to keys in `classlists_by_papernum`
            should have names and IDs stamped on the front.  Can be an empty
            dict or omitted.
        paperdir: where to find the papers to print; if None then use a
            default value.
        indexToCheck: the index of single paper to prename or (if None),
            then prename all.

    Returns:
        None

    Raises:
        RuntimeError: raised if any of the expected PDF files not found.
    """
    if paperdir is None:
        paperdir = Path(paperdir_name)
    paperdir = Path(paperdir)
    range_to_check: Iterable = []
    if indexToCheck:
        range_to_check = [indexToCheck]
    else:  # check production of all papers
        range_to_check = range(1, spec["numberToProduce"] + 1)
    # now check that paper(s) are actually on disk
    for papernum in range_to_check:
        r = classlist_by_papernum.get(papernum, None)
        if r:
            pdf_file = paperdir / f'exam_{papernum:04}_{r["id"]}.pdf'
            # if file is not there - error, else tell DB it is ID'd
            if not pdf_file.is_file():
                raise RuntimeError(f'Cannot find pdf for paper "{pdf_file}"')
            else:
                # push the student ID to the prediction-table in the database
                msgr.pre_id_paper(papernum, r["id"], predictor="prename")
        else:
            pdf_file = paperdir / f"exam_{papernum:04}.pdf"
            # if file is not there - error.
            if not pdf_file.is_file():
                raise RuntimeError(f'Cannot find pdf for paper "{pdf_file}"')
