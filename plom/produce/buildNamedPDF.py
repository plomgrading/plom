# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import os
from pathlib import Path
from multiprocessing import Pool
from tqdm import tqdm
import csv

from .mergeAndCodePages import make_PDF, make_fakePDF
from . import paperdir


def _make_PDF(x):
    """Call make_PDF from mergeAndCodePages with arguments expanded.

    *Note*: this is a little bit of glue to make the parallel Pool code
    elsewhere work.

    Arguments:
        x (tuple): this is expanded as the arguments to :func:`make_PDF`.
    """
    fakepdf = x[-1]  # look at last arg - x[-1] = fakepdf
    y = x[:-1]  # drop the last argument = fakepdf
    if fakepdf:
        make_fakePDF(*y)
    else:
        make_PDF(*y)


def outputProductionCSV(spec, make_PDF_args):
    """Output a csv with info on produced papers. Take the make_PDF_args that were used and dump them in a csv

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        make_PDF_args (list): a list of tuples of info for each paper
    """
    # a tuple in make_pdf_args is a tuple
    # 0 - spec["name"],
    # 1 - spec["publicCode"],
    # 2 - spec["numberOfPages"],
    # 3 - spec["numberOfVersions"],
    # 4 - paper_index,
    # 5 - page_version = dict(page:version)
    # 6 - student_info = dict(id:sid ,name:sname)
    # we only need the last 3 of these
    numberOfPages = spec["numberOfPages"]
    numberOfQuestions = spec["numberOfQuestions"]

    header = ["test_number", "sID", "sname"]
    for q in range(1, numberOfQuestions + 1):
        header.append("q{}.version".format(q))
    for p in range(1, numberOfPages + 1):
        header.append("p{}.version".format(p))
    with open("produced_papers.csv", "w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)
        for paper in make_PDF_args:
            if paper[6]:  # if named paper then give id and name
                row = [paper[4], paper[6]["id"], paper[6]["name"]]
            else:  # just skip those columns
                row = [paper[4], None, None]
            for q in range(1, numberOfQuestions + 1):
                # get first page of question to infer version
                p = spec["question"]["{}".format(q)]["pages"][0]
                row.append(paper[5][p])
            for p in range(1, numberOfPages + 1):
                row.append(paper[5][p])
            csv_writer.writerow(row)


def build_all_papers(
    spec, global_page_version_map, classlist, fakepdf=False, no_qr=False
):
    """Builds the papers using _make_PDF.

    Based on `numberToName` this uses `_make_PDF` to create some
    papers with names stamped on the front as well as some papers without.

    For the prenamed papers, names and IDs are taken in order from the
    classlist.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        global_page_version_map (dict): dict of dicts mapping first by
            paper number (int) then by page number (int) to version (int).
        classlist (list, None): ordered list of (sid, sname) pairs.
        fakepdf (bool): when true, the build empty pdfs (actually empty files)
            for use when students upload homework or similar (and only 1 version).

    Raises:
        ValueError: classlist is invalid in some way.
    """
    if spec["numberToName"] > 0:
        if not classlist:
            raise ValueError("You must provide a classlist to prename papers")
        if len(classlist) < spec["numberToName"]:
            raise ValueError(
                "Classlist is too short for {} pre-named papers".format(
                    spec["numberToName"]
                )
            )
    make_PDF_args = []
    for paper_index in range(1, spec["numberToProduce"] + 1):
        page_version = global_page_version_map[paper_index]
        if paper_index <= spec["numberToName"]:
            student_info = {
                "id": classlist[paper_index - 1][0],
                "name": classlist[paper_index - 1][1],
            }
        else:
            student_info = None
        make_PDF_args.append(
            (
                spec["name"],
                spec["publicCode"],
                spec["numberOfPages"],
                spec["numberOfVersions"],
                paper_index,
                page_version,
                student_info,
                no_qr,
                fakepdf,  # should be last
            )
        )

    # Same as:
    # for x in make_PDF_args:
    #     make_PDF(*x)
    num_PDFs = len(make_PDF_args)
    with Pool() as pool:
        r = list(tqdm(pool.imap_unordered(_make_PDF, make_PDF_args), total=num_PDFs))
    # output CSV with all this info in it
    print("Writing produced_papers.csv.")
    outputProductionCSV(spec, make_PDF_args)


def confirm_processed(spec, msgr, classlist):
    """Checks that each PDF file was created and notify server.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        msgr (Messenger): an open active connection to the server.
        classlist (list, None): ordered list of (sid, sname) pairs.

    Raises:
        RuntimeError: raised if any of the expected PDF files not found.
        ValueError: classlist is invalid in some way.
    """
    if spec["numberToName"] > 0:
        if not classlist:
            raise ValueError("You must provide a classlist for pre-named papers")
        if len(classlist) < spec["numberToName"]:
            raise ValueError(
                "Classlist is too short for {} pre-named papers".format(
                    spec["numberToName"]
                )
            )
    for paper_index in range(1, spec["numberToProduce"] + 1):
        if paper_index <= spec["numberToName"]:
            PDF_file_name = Path(paperdir) / "exam_{}_{}.pdf".format(
                str(paper_index).zfill(4), classlist[paper_index - 1][0]
            )
        else:
            PDF_file_name = Path(paperdir) / "exam_{}.pdf".format(
                str(paper_index).zfill(4)
            )

        # We will raise and error if the pdf file was not found
        if os.path.isfile(PDF_file_name):
            msgr.notify_pdf_of_paper_produced(paper_index)
        else:
            raise RuntimeError('Cannot find pdf for paper "{}"'.format(PDF_file_name))


def identify_prenamed(spec, msgr, classlist):
    """Identify papers that pre-printed names on the server.

    Arguments:
        spec (dict): exam specification, see :func:`plom.SpecVerifier`.
        msgr (Messenger): an open active connection to the server.
        classlist (list, None): ordered list of (sid, sname) pairs.

    Raises:
        RuntimeError: raised if any of the expected PDF files not found.
        ValueError: classlist is invalid in some way.
    """
    if spec["numberToName"] > 0:
        if not classlist:
            raise ValueError("You must provide a classlist to prename papers")
        if len(classlist) < spec["numberToName"]:
            raise ValueError(
                "Classlist is too short for {} pre-named papers".format(
                    spec["numberToName"]
                )
            )
    for paper_index in range(1, spec["numberToProduce"] + 1):
        if paper_index <= spec["numberToName"]:
            sid, sname = classlist[paper_index - 1]
            PDF_file_name = Path(paperdir) / "exam_{}_{}.pdf".format(
                str(paper_index).zfill(4), sid
            )
            if os.path.isfile(PDF_file_name):
                msgr.id_paper(paper_index, sid, sname)
            else:
                raise RuntimeError(
                    'Cannot find pdf for paper "{}"'.format(PDF_file_name)
                )
