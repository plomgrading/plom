# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

"""Plom's frontend scanning routines for self-scanned work.

There are two main approaches to uploading: Test Pages and Homework Pages.
This module deals with "Homework Pages", self-scanned work typically
without QR-codes that are associated with a particular known student but
are unstructured or understructured in the their relationship to the exam
template.

If you instead are dealing with QR-coded pages where you may not yet know
which pages belong to which student, see :py:module:`frontend_scan`.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import fitz
import tomlkit

from plom.scan.sendPagesToServer import (
    does_bundle_exist_on_server,
    createNewBundle,
    upload_HW_pages,
    checkTestHasThatSID,
)
from plom.scan.bundle_utils import (
    get_bundle_dir,
    # make_bundle_dir,
    bundle_name_and_md5_from_file,
    archiveHWBundle,
)
from plom.scan.question_list_utils import canonicalize_page_question_map
from plom.scan.hwSubmissionsCheck import IDQorIDorBad
from plom.scan.scansToImages import process_scans
from plom.scan import with_scanner_messenger


@with_scanner_messenger
def processHWScans(
    pdf_fname,
    student_id: str,
    questions,
    *,
    msgr,
    gamma: bool = False,
    extractbmp: bool = False,
    basedir: Path = Path("."),
    bundle_name: str | None = None,
):
    """Process the given PDF bundle into images, upload, then archive the pdf.

    Args:
        pdf_fname (pathlib.Path/str): path to a PDF file.  Need not be in
            the current working directory.
        student_id: the student ID to upload this to.
        questions (list): to which questions should we upload these pages?

              * a scalar number: all pages map to this question.
              * a list of integers: all pages map to those questions.
              * the string "all" maps each page to all questions.
              * a list-of-lists specifying which questions each page
                maps onto, e.g., ``[[1],[1,2],[2]]`` maps page 1 onto
                question 1, page 2 onto questions 1 and 2, and page 3
                onto question 2.

            Any string input will parsed to find the above options.
            Tuples or other iterables should be in place of lists.
            TODO: Currently `dict` are not supported, subject to change.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        basedir (pathlib.Path): where on the file system do we perform
            the work.  By default, the current working directory is used.
            Subdirectories "archivePDFs" and "bundles" will be created.
        bundle_name: Override the bundle name (which is by
            default is generated from the PDF filename).
        gamma: do gamma correction
        extractbmp: whether to try extracting bitmaps instead of the default
            of rendering the page image.

    Returns:
        None

    Raises:
        ValueError: various errors such as cannot find file, no such student
            id, md5sum collision with existing bundle, etc.  Generally
            things caller could fix.  Check message for details.
        RuntimeError: expected failing conditions.
        TODO: possibly others, need to drill into ``process_scans`` and
            other methods.

    Ask server to map `student_id` to a test-number; these should have been
    pre-populated on test-generation or just-in-time before calling this
    so if `student_id` not known there is an error.

    Turn `pdf_fname` into a bundle name and check with server if that
    bundle_name / md5sum known.

      - abort if name xor md5sum known,
      - continue otherwise (when both name / md5sum known we assume this is resuming after a crash).

    Process PDF into images.

    Ask server to create the bundle, which tells us the `skip_list`
    which is a list of bundle-orders (i.e., page number within the PDF)
    that have already been uploaded. In typical use this will be empty.

    Then upload pages to the server if not in skip list.
    Finally archive the bundle.
    """
    pdf_fname = Path(pdf_fname)
    if not pdf_fname.is_file():
        raise ValueError(f"Cannot find file {pdf_fname}")

    if len(questions) == 1:
        qlabel = "question"
    else:
        qlabel = "questions"
    print(
        "Process and upload file {} as answer to {} {} for sid {}".format(
            pdf_fname.name, qlabel, questions, student_id
        )
    )

    N = msgr.get_spec()["numberOfQuestions"]
    with fitz.open(pdf_fname) as pdf:
        num_pages = len(pdf)
    questions = canonicalize_page_question_map(
        questions, pages=num_pages, numquestions=N
    )

    test_number = checkTestHasThatSID(student_id, msgr=msgr)
    if test_number is None:
        raise ValueError(f"No test has student ID {student_id}")
    else:
        print(f"Student ID {student_id} is test_number {test_number}")

    _, md5 = bundle_name_and_md5_from_file(pdf_fname)
    if not bundle_name:
        bundle_name = _
    exists, reason = does_bundle_exist_on_server(bundle_name, md5, msgr=msgr)
    assert bundle_name is not None
    if exists:
        if reason == "name":
            raise ValueError(
                f'The bundle "{bundle_name}" has been used previously for a different bundle'
            )
        elif reason == "md5sum":
            raise ValueError(
                "A bundle with matching md5sum is already in system with a different name"
            )
        elif reason == "both":
            print(
                f'Warning - bundle "{bundle_name}" has been declared previously - you are likely trying again as a result of a crash. Continuing'
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path! File issue")

    bundledir = get_bundle_dir(bundle_name, basedir=basedir)

    with open(bundledir / "source.toml", "w") as f:
        tomlkit.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    files = process_scans(pdf_fname, bundledir, not gamma, not extractbmp)

    print(f'Trying to create bundle "{pdf_fname}" on server')
    exists, extra = createNewBundle(bundle_name, md5, msgr=msgr)
    if exists:
        skip_list = extra
        if len(skip_list) > 0:
            print("Some images from that bundle were uploaded previously:")
            print("Pages {}".format(skip_list))
            print("Skipping those images.")
    elif extra == "name":
        raise ValueError("Different bundle with same name was previously uploaded.")
    elif extra == "md5sum":
        raise ValueError("Bundle with same md5sum different name previously uploaded.")
    else:
        raise RuntimeError("Should not be here: unexpected code path! File issue")

    assert len(files) == num_pages, "Inconsistent page counts, something bad happening!"
    file_list = zip(range(1, num_pages + 1), files, questions)

    # TODO: filter skiplist for already uploaded files
    assert len(skip_list) == 0, "TODO: we don't really support skiplist for HW pages"

    # send the images to the server
    upload_HW_pages(file_list, bundle_name, bundledir, student_id, msgr=msgr)
    # now archive the PDF
    archiveHWBundle(pdf_fname, basedir=basedir)


def processAllHWByQ(server, password, yes_flag):
    """Process and upload all HW by Q bundles in submission directory.

    Scan through the submittedHWByQ directory and process/upload
    each PDF in turn. User will be prompted for each unless the
    'yes_flag' is set.
    """
    submissions = defaultdict(list)
    for file_name in sorted(Path("submittedHWByQ").glob("*.pdf")):
        IDQ = IDQorIDorBad(file_name)
        if len(IDQ) == 3:
            sid, q = IDQ[1:]
            if q != "_":
                submissions[sid].append([q, file_name])

    print("Submission summary: ")
    for sid in submissions:
        sub_list = sorted([int(x[0]) for x in submissions[sid]])
        print_list = []
        for q in range(sub_list[0], sub_list[-1] + 1):
            n = sub_list.count(q)
            if n == 0:
                continue
            elif n == 1:
                print_list.append("{}".format(q))
            else:
                print_list.append("{}(x{})".format(q, n))
        print("# {}: {}".format(sid, print_list))

    if yes_flag:
        print("Processing and uploading all of the above submissions.")
    elif input("Process and upload all of the above submissions? [y/n]") != "y":
        print("Stopping.")
        return
    for sid in submissions:
        print("Processing id {}:".format(sid))
        for question, file_name in submissions[sid]:
            processHWScans(file_name, sid, [int(question)], msgr=(server, password))


@with_scanner_messenger
def processMissing(*, msgr, yes_flag):
    """Replace missing questions with 'not submitted' pages.

    Student may not upload pages for questions they don't answer. This function
    asks server for list of all missing hw-questions from all tests that have
    been used (but are not complete). The server only returns questions that
    have neither hw-pages nor t-pages - so any partially scanned tests with
    tpages are avoided.

    For each remaining test we replace each missing question with a 'question not submitted' page.
    The user will be prompted in each case unless the 'yes_flag' is set.
    """
    missingHWQ = msgr.getMissingHW()
    # returns list for each test [sid, list of missing hwq]
    for t in missingHWQ:
        print(f"Student {missingHWQ[t][0]}'s paper is missing questions")

    if len(missingHWQ) == 0:
        print("All papers either complete or have scanned test-pages present.")
        return

    if yes_flag:
        print("Replacing all missing questions with 'did not submit' pages.")
    elif input("Replace all missing with 'did not submit' pages? [y/n]") != "y":
        print("Stopping.")
        return

    for t in missingHWQ:
        sid = missingHWQ[t][0]
        for q in missingHWQ[t][1:]:
            print("Replacing q{} of sid {}".format(q, sid))
            # this call can replace by SID or by test-number
            msgr.replaceMissingHWQuestion(student_id=sid, test=None, question=q)
