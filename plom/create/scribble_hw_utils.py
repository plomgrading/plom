# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

"""Plom tools for scribbling fake homework answers for testing purposes."""

from pathlib import Path
import random

import fitz

from plom.create.scribble_utils import possible_answers


def makeFakeHW(numQuestions, paperNum, who, where, prefix, maxpages=3):
    # TODO: Issue #1646 here we want student number with id fallback?
    student_num = who["id"]
    name = who["name"]
    did = random.randint(numQuestions - 1, numQuestions)  # some subset of questions
    doneQ = sorted(random.sample(list(range(1, 1 + numQuestions)), did))
    for q in doneQ:
        fname = where / "{}.{}.{}.pdf".format(prefix, student_num, q)
        with fitz.open() as doc:
            scribble_doc(doc, student_num, name, maxpages, q)
            doc.save(fname)


def makeFakeHW2(numQuestions, paperNum, who, where, prefix, maxpages=4):
    # TODO: Issue #1646 here we want student number with id fallback?
    student_num = who["id"]
    name = who["name"]
    doneQ = list(range(1, 1 + numQuestions))
    fname = where / "{}.{}.{}.pdf".format(prefix, student_num, "_")
    with fitz.open() as doc:
        for q in doneQ:
            scribble_doc(doc, student_num, name, maxpages, q)
        doc.save(fname)


def scribble_doc(doc, student_num, name, maxpages, q):
    if True:
        # construct pages
        for pn in range(random.randint(1, maxpages)):
            page = doc.new_page(-1, 612, 792)  # page at end
            if pn == 0:
                # put name and student number on p1 of the Question
                rect1 = fitz.Rect(24, 24, page.rect.width - 24, 100)
                rc = page.insert_textbox(
                    rect1,
                    f"Q.{q} - {name}:{student_num}",
                    fontsize=14,
                    color=[0.1, 0.1, 0.1],
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                # page.draw_rect(rect1, color=(1, 0, 0), width=0.25)
                assert rc > 0, f"overfull fitz textbox by {rc}"

            rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            text = random.choice(possible_answers)
            rc = page.insert_textbox(
                rect,
                text,
                fontsize=13,
                color=[0.1, 0.1, 0.8],
                fontname="helv",
                fontfile=None,
                align=0,
            )
            # page.draw_rect(rect, color=(1, 0, 0), width=0.25)
            assert rc > 0, f"overfull fitz textbox by {rc}"


def download_classlist_and_spec(server=None, password=None):
    """Download list of student IDs/names and test specification from server."""
    # I had some mypy trouble from this import so I hid it down here
    from plom.create import start_messenger

    msgr = start_messenger(server, password)
    try:
        classlist = msgr.IDrequestClasslist()
        spec = msgr.get_spec()
    finally:
        msgr.closeUser()
        msgr.stop()
    return classlist, spec


def make_hw_scribbles(server, password, basedir=Path("."), how_many=10):
    """Fake homework submissions by scribbling on the pages of blank tests.

    Args:
        server (str): the name and port of the server.
        password (str): the "manager" password.
        basedir (str/pathlib.Path): the blank tests (for scribbling) will
            be taken from `basedir/papersToPrint`.  The pdf files with
            scribbles will be created in `basedir/submittedHWByQ`.
        how_many (int): how many hws to create

    1. Read in the existing papers.
    2. Create the fake data filled pdfs
    3. Generates second batch for first half of papers.
    4. Generates some "semiloose" bundles; those that have all questions
       or more than one question in a single bundle.
    """
    classlist, spec = download_classlist_and_spec(server, password)
    numberOfQuestions = spec["numberOfQuestions"]

    d = Path(basedir) / "submittedHWByQ"
    d.mkdir(exist_ok=True)

    all_in_one_bundle = (
        4  # how many students with all questions in a single file = semiloose
    )
    one_q_per_bundle = (
        how_many - all_in_one_bundle
    )  # how many students with one question per file = hwA
    # half of this get a second file for each question - ie student submits two files per q. = hwB
    second_one_q_per_bundle = one_q_per_bundle // 2

    for k in range(one_q_per_bundle):
        makeFakeHW(numberOfQuestions, k, classlist[k], d, "hwA")

    for k in range(second_one_q_per_bundle):
        makeFakeHW(numberOfQuestions, k, classlist[k], d, "hwB", maxpages=1)

    # a few more for "all questions in one" bundling
    for k in range(how_many - one_q_per_bundle, how_many):
        makeFakeHW2(numberOfQuestions, k, classlist[k], d, "semiloose")
