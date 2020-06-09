#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import os
from pathlib import Path
from multiprocessing import Pool
from tqdm import tqdm

from plom import specdir
from plom.db import PlomDB
from .mergeAndCodePages import make_PDF
from . import paperdir


# TODO: maybe functions in this module should expect classlist as an input?
# TODO: its a bit strange to be reading the class list here.
#
# TODO: even worse, the row indices are mapped to test numbers in a way that
# TODO: may not be obvious (the `confirmedNamed` fcn).  Needs some re-org.


def read_class_list():
    """Creates a dictionary of the students name and ids and returns it

    TODO: Perhaps this function should be reformatted

    Returns:
        dict -- A dictionary of the form {int: list[Str, Str]} with:
                - Index integer is the key
                - List of student id and student name is the value
    """
    students = {}
    # read in the classlist
    with open(Path(specdir) / "classlist.csv", newline="") as csvfile:
        red = csv.reader(csvfile, delimiter=",")
        next(red, None)
        k = 0
        for row in red:
            k += 1
            students[k] = [row[0], row[1]]

    return students


def _make_PDF(x):
    """Call make_PDF from mergeAndCodePages with arguments expanded.

    *Note*: this is a little bit of glue to make the parallel Pool code
    elsewhere work.

    Arguments:
        x (tuple): this is expanded as the arguments to :func:`make_PDF`.
    """
    make_PDF(*x)


def build_all_papers(spec, global_page_version_map, named=False):
    """Builds the papers using _make_PDF.

    Based on `numberToName` this uses `_make_PDF` to create some
    papers with names stamped on the front as well as some papers without.

    Arguments:
        spec {dict} -- A dictionary embedding the exam info. This dictionary does not have a normal format.
                       Example below:
                       {
                       'name': 'plomdemo',
                       'longName': 'Midterm Demo using Plom',
                       'numberOfVersions': 2,
                       'numberOfPages': 6,
                       'numberToProduce': 20,
                       'numberToName': 10,
                       'numberOfQuestions': 3,
                       'privateSeed': '1001378822317872',
                       'publicCode': '270385',
                       'idPages': {'pages': [1]},
                       'doNotMark': {'pages': [2]},
                       'question': {
                           '1': {'pages': [3], 'mark': 5, 'select': 'shuffle'},
                           '2': {'pages': [4], 'mark': 10, 'select': 'fix'},
                           '3': {'pages': [5, 6], 'mark': 10, 'select': 'shuffle'} }
                          }
                       }
        global_page_version_map (dict): dict of dicts mapping first by
            paper number (int) then by page number (int) to version (int).

    Keyword Arguments:
        named {boolean} -- Whether the document is named or not. (default: {False})
    """

    if named and spec["numberToName"] > 0:
        # TODO: get from server
        students = read_class_list()

    make_PDF_args = []
    for paper_index in range(1, spec["numberToProduce"] + 1):
        page_version = global_page_version_map[paper_index]
        if named and paper_index <= spec["numberToName"]:
            student_info = {
                "id": students[paper_index][0],
                "name": students[paper_index][1],
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
            )
        )

    # Same as:
    # for x in make_PDF_args:
    #     make_PDF(*x)
    num_PDFs = len(make_PDF_args)
    with Pool() as pool:
        r = list(tqdm(pool.imap_unordered(_make_PDF, make_PDF_args), total=num_PDFs))


def confirm_processed(spec, DB_file_name):
    """A function that checks if the pdfs are created in the correct folder.

    Arguments:
        spec {type} -- A dictionary embedding the exam info. This dictionary does not have a normal format.
        DB_file_name {Str} -- Database file name path

    Raises:
        RuntimeError: Runtime error thrown if the pdf file is not found
    """

    exam_DB = PlomDB(DB_file_name)
    if spec["numberToName"] > 0:
        students = read_class_list()
    for paper_index in range(1, spec["numberToProduce"] + 1):
        # TODO: explain this better, we need to consider the nameless papers
        if paper_index <= spec["numberToName"]:
            PDF_file_name = Path(paperdir) / "exam_{}_{}.pdf".format(
                str(paper_index).zfill(4), students[paper_index][0]
            )
        else:
            PDF_file_name = Path(paperdir) / "exam_{}.pdf".format(
                str(paper_index).zfill(4)
            )

        # We will raise and error if the pdf file was not found
        # TODO: what does this do?  What do we need from server?
        if os.path.isfile(PDF_file_name):
            exam_DB.produceTest(paper_index)
        else:
            raise RuntimeError('Cannot find pdf for paper "{}"'.format(PDF_file_name))


def confirm_named(spec, DB_file_name):
    """Confirms that each paper in the spec has a corresponding PDF present.

    TODO: also identifies them?!  Poor name "confirm" if so...

    Arguments:
        spec {dict} -- A dictionary embedding the exam info. This dictionary does not have a normal format.
                          Example: See description for build_all_papers
        DB_file_name {Str} -- Database file name path

    Raises:
        RuntimeError: Runtime error thrown if the pdf file is not found
    """

    exam_DB = PlomDB(DB_file_name)
    if spec["numberToName"] > 0:
        students = read_class_list()
    for paper_index in range(1, spec["numberToProduce"] + 1):
        if paper_index <= spec["numberToName"]:
            PDF_file_name = Path(paperdir) / "exam_{}_{}.pdf".format(
                str(paper_index).zfill(4), students[paper_index][0]
            )
            if os.path.isfile(PDF_file_name):
                # TODO: replace with api call
                exam_DB.identifyTest(
                    paper_index, students[paper_index][0], students[paper_index][1]
                )
            else:
                raise RuntimeError(
                    'Cannot find pdf for paper "{}"'.format(PDF_file_name)
                )
