# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""Plom's frontend scanning routines for self-scanned work.

There are two main approaches to uploading: Test Pages and Homework Pages.
This module deals with "Homework Pages", self-scanned work typically
without QR-codes that are associated with a particular known student but
are unstructured or understructured in the their relationship to the exam
template.

If you instead are dealing with QR-coded pages where you may not yet know
which pages belong to which student, see :py:module:`frontend_scan`.
"""

import ast
from collections import defaultdict
import os
from pathlib import Path

import fitz
import toml

from plom.scan.sendPagesToServer import (
    does_bundle_exist_on_server,
    createNewBundle,
    uploadLPages,
    upload_HW_pages,
    checkTestHasThatSID,
)
from plom.scan.bundle_utils import (
    get_bundle_dir,
    make_bundle_dir,
    bundle_name_and_md5_from_file,
    archiveLBundle,
    archiveHWBundle,
)
from plom.scan.checkScanStatus import get_number_of_questions
from plom.scan.hwSubmissionsCheck import IDQorIDorBad
from plom.scan.scansToImages import process_scans
from plom.scan import checkScanStatus


def processLooseScans(
    server, password, pdf_fname, student_id, gamma=False, extractbmp=False
):
    """Process the given Loose-pages PDF into images, upload then archive the pdf.

    pdf_fname should be for form 'submittedLoose/blah.XXXX.pdf'
    where XXXX should be student_id. Do basic sanity check to confirm.

    Ask server to map student_id to a test-number; these should have been
    pre-populated on test-generation and if id not known there is an error.

    Turn pdf_fname in to a bundle_name and check with server if that bundle_name / md5sum known.
     - abort if name xor md5sum known,
     - continue otherwise (when both name / md5sum known we assume this is resuming after a crash).

    Process PDF into images.

    Ask server to create the bundle - it will return an error or [True, skip_list]. The skip_list is a list of bundle-orders (ie page number within the PDF) that have already been uploaded. In typical use this will be empty.

    Then upload pages to the server if not in skip list (this will trigger a server-side update when finished). Finally archive the bundle.
    """
    pdf_fname = Path(pdf_fname)
    if not pdf_fname.is_file():
        print("Cannot find file {} - skipping".format(pdf_fname))
        return

    assert os.path.split(pdf_fname)[0] in [
        "submittedLoose",
        "./submittedLoose",
    ], 'At least for now, you must your file into a directory named "submittedLoose"'
    IDQ = IDQorIDorBad(pdf_fname.name)
    if len(IDQ) != 2:  # should return [JID, sid]
        print("File name has wrong format. Should be 'blah.sid.pdf'. Stopping.")
        return
    sid = IDQ[1]
    if sid != student_id:
        print(
            "Student ID supplied {} does not match that in filename {}. Stopping.".format(
                student_id, sid
            )
        )
        return
    print(
        "Process and upload file {} as loose pages for sid {}".format(
            pdf_fname.name, student_id
        )
    )

    bundle_name, md5 = bundle_name_and_md5_from_file(pdf_fname)
    exists, reason = does_bundle_exist_on_server(bundle_name, md5, server, password)
    if exists:
        if reason == "name":
            print(
                f'The bundle "{bundle_name}" has been used previously for a different bundle'
            )
            return
        elif reason == "md5sum":
            print(
                "A bundle with matching md5sum is already in system with a different name"
            )
            return
        elif reason == "both":
            print(
                f'Warning - bundle "{bundle_name}" has been declared previously - you are likely trying again as a result of a crash. Continuing'
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path! File issue")

    bundledir = Path("bundles") / "submittedLoose" / bundle_name
    make_bundle_dir(bundledir)

    with open(bundledir / "source.toml", "w") as f:
        toml.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    process_scans(pdf_fname, bundledir, not gamma, not extractbmp)

    print("Creating bundle for {} on server".format(pdf_fname))
    rval = createNewBundle(bundle_name, md5, server, password)
    # should be [True, skip_list] or [False, reason]
    if rval[0]:
        skip_list = rval[1]
        if len(skip_list) > 0:
            print("Some images from that bundle were uploaded previously:")
            print("Pages {}".format(skip_list))
            print("Skipping those images.")
    else:
        print("There was a problem with this bundle.")
        if rval[1] == "name":
            print("A different bundle with the same name was uploaded previously.")
        else:
            print(
                "A bundle with matching md5sum but different name was uploaded previously."
            )
        print("Stopping.")
        return

    # send the images to the server
    uploadLPages(bundle_name, skip_list, student_id, server, password)
    # now archive the PDF
    archiveLBundle(pdf_fname)


def _parse_questions(s):
    if isinstance(s, str):
        if s.casefold() == "all":
            return "all"
        s = ast.literal_eval(s)
    return s


def canonicalize_question_list(s, pages, numquestions):
    """Make a canonical page-to-questions mapping from various shorthand inputs.

    args:
        s (str/list/tuple): the input, can be a special string "all"
            or a string which we will parse.  Or an integer.  Or a list
            of ints, or a list of list of ints.
        pages (int): how many pages, used for checking input.
        numquestins (int): how many questions total, used for checking
            input.
    """
    s = _parse_questions(s)
    if s == "all":
        s = range(1, numquestions + 1)

    if isinstance(s, str):
        raise ValueError('question cannot be a string, unless its "all"')

    if isinstance(s, int):
        s = [s]

    if isinstance(s, dict):
        raise NotImplementedError("a dict seems very sensible but is not implemented")

    # TypeError if not iterable
    iter(s)

    # are the contents themselves iterable?
    try:
        iter(s[0])
    except TypeError:
        # if not, repeat the list for each page
        s = [s] * pages

    if len(s) != pages:
        raise ValueError(f"list too short: need one list for each of {pages} pages")

    # cast to lists
    s = [list(qlist) for qlist in s]

    # finally we should have a canonical list-of-lists-of-ints
    for qlist in s:
        for qnum in qlist:
            if not isinstance(qnum, int):
                raise ValueError(f"non-integer question value {qnum}")
            if qnum < 1 or qnum > numquestions:
                raise ValueError(f"question value {qnum} outside [1, {numquestions}]")
    return s


def processHWScans(
    server,
    password,
    pdf_fname,
    student_id,
    questions,
    *,
    gamma=False,
    extractbmp=False,
    basedir=Path("."),
    bundle_name=None,
):
    """Process the given PDF bundle into images, upload, then archive the pdf.

    args:
        server (str)
        password (str)
        pdf_fname (pathlib.Path/str): path to a PDF file.  Need not be in
            the current working directory.
        student_id (str)
        questions (list): to which questions should we upload the pages
            of this bundle?
              * a scalar number: all pages map to this question.
              * a list of integers: all pages map to those questions.
              * the string "all" maps each pages to all questions.
              * a list-of-lists specifying which questions each page
                maps onto, e.g., `[[1],[1,2],[2]]` maps page 1 onto
                question 1, page 2 onto questions 1 and 2, and page 3
                onto question 2.
            Any string input will parsed to find the above options.
            Tuples or other iterables should be in place of lists.
            TODO: Currently `dict` are not supported, subject to change.

    kwargs:
        basedir (pathlib.Path): where on the file system do we perform
            the work.  By default, the current working directory is used.
            Subdirectories "archivePDFs" and "bundles" will be created.
        bundle_name (str/None): Override the bundle name (which is by
            default is generated from the PDF filename).
        gamma (bool):
        extractbmp (bool):

    returns:
        None

    Ask server to map student_id to a test-number; these should have been
    pre-populated on test-generation and if id not known there is an error.

    Turn pdf_fname in to a bundle_name and check with server if that bundle_name / md5sum known.
     - abort if name xor md5sum known,
     - continue otherwise (when both name / md5sum known we assume this is resuming after a crash).

    Process PDF into images.

    Ask server to create the bundle, which tells us the `skip_list`
    which is a list of bundle-orders (i.e., page number within the PDF)
    that have already been uploaded. In typical use this will be empty.

    Then upload pages to the server if not in skip list (this will trigger a server-side update when finished). Finally archive the bundle.
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

    N = get_number_of_questions(server, password)
    num_pages = len(fitz.open(pdf_fname))
    questions = canonicalize_question_list(questions, pages=num_pages, numquestions=N)

    test_number = checkTestHasThatSID(student_id, server, password)
    if test_number is None:
        raise ValueError(f"No test has student ID {student_id}")
    else:
        print(f"Student ID {student_id} is test_number {test_number}")

    _, md5 = bundle_name_and_md5_from_file(pdf_fname)
    if not bundle_name:
        bundle_name = _
    exists, reason = does_bundle_exist_on_server(bundle_name, md5, server, password)
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
        toml.dump({"file": str(pdf_fname), "md5": md5}, f)

    print("Processing PDF {} to images".format(pdf_fname))
    files = process_scans(pdf_fname, bundledir, not gamma, not extractbmp)

    print(f'Trying to create bundle "{pdf_fname}" on server')
    exists, extra = createNewBundle(bundle_name, md5, server, password)
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
    upload_HW_pages(file_list, bundle_name, bundledir, student_id, server, password)
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
            processHWScans(server, password, file_name, sid, [int(question)])


def processMissing(server, password, *, yes_flag):
    """Replace missing questions with 'not submitted' pages

    Student may not upload pages for questions they don't answer. This function
    asks server for list of all missing hw-questions from all tests that have
    been used (but are not complete).

    For each test we check if any test-pages are present and skip if they are.

    For each remaining test we replace each missing question with a 'question not submitted' page. The user will be prompted in each case unless the 'yes_flag' is set.
    """
    missingHWQ = checkScanStatus.checkMissingHWQ(server, password)
    # returns list for each test [scanned-tpages-present boolean, sid, missing-question-numbers]
    reallyMissing = {}  # new list of those without tpages present
    for t in missingHWQ:
        if missingHWQ[t][0]:  # scanned test-pages present, so no replacing.
            print(
                "Student {}'s paper has tpages present, so skipping".format(
                    missingHWQ[t][1]
                )
            )
        else:
            print(
                "Student {} is missing questions {}".format(
                    missingHWQ[t][1], missingHWQ[t][2:]
                )
            )
            reallyMissing[t] = missingHWQ[t]

    if len(reallyMissing) == 0:
        print("All papers either complete or have scanned test-pages present.")
        return

    if yes_flag:
        print("Replacing all missing questions with 'did not submit' pages.")
    elif input("Replace all missing with 'did not submit' pages? [y/n]") != "y":
        print("Stopping.")
        return

    for t in reallyMissing:
        sid = reallyMissing[t][1]
        for q in reallyMissing[t][2:]:
            print("Replacing q{} of sid {}".format(q, sid))
            checkScanStatus.replaceMissingHWQ(server, password, sid, q)
