#!/usr/bin/env python3

# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom tools for scanning homework and pushing to servers."""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
from collections import defaultdict
import glob
import os
from pathlib import Path

from plom import __version__
from plom.scan import bundle_name_and_md5
from plom.scan import get_number_of_questions
from plom.scan.hwSubmissionsCheck import IDQorIDorBad


def clearLogin(server, password):
    from plom.scan import clearScannerLogin

    clearScannerLogin.clearLogin(server, password)


def scanStatus(server, password):
    """Prints summary of test/hw uploads.

    More precisely. Prints lists
    * which tests have been used (ie at least one uploaded page)
    * which tests completely scanned (both tpages and hwpage)
    * incomplete tests (missing one tpage or one hw-question)
    """

    from plom.scan import checkScanStatus

    checkScanStatus.checkStatus(server, password)


def whoDidWhat(server, password, directory_check):
    """Prints lists of hw/loose submissions on server / local

    * Prints list of hw-submissions already uploaded to server
    * Prints list of what hw-submissions are in the current submittedHWByQ directory
    * Prints list of what loose-submissions are in the current submittedLoose directory
    """
    from plom.scan.hwSubmissionsCheck import whoSubmittedWhat

    whoSubmittedWhat(server, password, directory_check)


def make_required_directories(bundle=None):
    os.makedirs("archivedPDFs", exist_ok=True)
    os.makedirs("archivedPDFs" / Path("submittedHWByQ"), exist_ok=True)
    os.makedirs("archivedPDFs" / Path("submittedLoose"), exist_ok=True)
    os.makedirs("bundles", exist_ok=True)
    # TODO: split up a bit, above are global, below per bundle
    if bundle:
        directory_list = [
            "uploads/sentPages",
            "uploads/discardedPages",
            "uploads/collidingPages",
            "uploads/sentPages/unknowns",
            "uploads/sentPages/collisions",
        ]
        for dir in directory_list:
            os.makedirs(bundle / Path(dir), exist_ok=True)


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
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer

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

    bundle_exists = sendPagesToServer.doesBundleExist(pdf_fname, server, password)
    # should be [False] [True, name] [True,md5sum], [True, both]
    if bundle_exists[0]:
        if bundle_exists[1] == "name":
            print(
                "The bundle name {} has been used previously for a different bundle. Stopping".format(
                    pdf_fname
                )
            )
            return
        elif bundle_exists[1] == "md5sum":
            print(
                "A bundle with matching md5sum is already in system with a different name. Stopping".format(
                    pdf_fname
                )
            )
            return
        elif bundle_exists[1] == "both":
            print(
                "Warning - bundle {} has been declared previously - you are likely trying again as a result of a crash. Continuing".format(
                    pdf_fname
                )
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path!")

    bundle_name, md5 = bundle_name_and_md5(pdf_fname)
    bundledir = Path("bundles") / "submittedLoose" / bundle_name
    make_required_directories(bundledir)

    print("Processing PDF {} to images".format(pdf_fname))
    scansToImages.processScans(pdf_fname, bundledir, not gamma, not extractbmp)

    print("Creating bundle for {} on server".format(pdf_fname))
    rval = sendPagesToServer.createNewBundle(bundle_name, md5, server, password)
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
    sendPagesToServer.uploadLPages(bundle_name, skip_list, student_id, server, password)
    # now archive the PDF
    scansToImages.archiveLBundle(pdf_fname)


def processHWScans(
    server,
    password,
    pdf_fname,
    student_id,
    questions,
    gamma=False,
    extractbmp=False,
):
    """Process the given HW PDF into images, upload then archive the pdf.

    TODO: relax filename!  Currently .YY. must be present but is ignored.

    pdf_fname should be for form 'submittedHWByQ/blah.XXXX.YY.pdf'
    where XXXX should be student_id and YY should be question_number.
    Do basic sanity checks to confirm.

    Ask server to map student_id to a test-number; these should have been
    pre-populated on test-generation and if id not known there is an error.

    Turn pdf_fname in to a bundle_name and check with server if that bundle_name / md5sum known.
     - abort if name xor md5sum known,
     - continue otherwise (when both name / md5sum known we assume this is resuming after a crash).

    Process PDF into images.

    Ask server to create the bundle - it will return an error or [True, skip_list]. The skip_list is a list of bundle-orders (ie page number within the PDF) that have already been uploaded. In typical use this will be empty.

    Then upload pages to the server if not in skip list (this will trigger a server-side update when finished). Finally archive the bundle.

    args:
        ...
        questions (list): list of integers of which questions this
            bundle covers.
    """
    from plom.scan import scansToImages
    from plom.scan import sendPagesToServer

    if not isinstance(questions, list):
        raise ValueError("You must pass a list of ints for `questions`")
    for q in questions:
        if not isinstance(q, int):
            raise ValueError("You must pass a list of ints for `questions`")

    pdf_fname = Path(pdf_fname)
    if not pdf_fname.is_file():
        print("Cannot find file {} - skipping".format(pdf_fname))
        return

    assert os.path.split(pdf_fname)[0] in [
        "submittedHWByQ",
        "./submittedHWByQ",
    ], 'At least for now, you must put your file into a directory named "submittedHWByQ"'
    IDQ = IDQorIDorBad(pdf_fname.name)
    if len(IDQ) != 3:  # should return [IDQ, sid, q]
        raise ValueError("File name has wrong format - should be 'blah.sid.q.pdf'.")
    _, sid, q = IDQ
    if sid != student_id:
        raise ValueError(
            "Student ID supplied {} does not match that in filename {}. Stopping.".format(
                student_id, sid
            )
        )
    # either we're dealing with multiquestions or we have exactly one question
    if not (q == "_" or [int(q)] == questions):
        raise ValueError(
            "Question supplied {} does not match that in filename {}. Stopping.".format(
                questions, q
            )
        )
    if len(questions) == 1:
        qlabel = "question"
    else:
        qlabel = "questions"
    print(
        "Process and upload file {} as answer to {} {} for sid {}".format(
            pdf_fname.name, qlabel, questions, student_id
        )
    )

    test_number = sendPagesToServer.checkTestHasThatSID(student_id, server, password)
    if test_number is None:
        raise ValueError("No test has student ID = {}.".format(student_id))
    else:
        print("Student ID {} is test_number {}".format(student_id, test_number))

    bundle_exists = sendPagesToServer.doesBundleExist(pdf_fname, server, password)
    # should be [False] [True, name] [True,md5sum], [True, both]
    if bundle_exists[0]:
        if bundle_exists[1] == "name":
            raise ValueError(
                "The bundle name {} has been used previously for a different bundle.".format(
                    pdf_fname
                )
            )
        elif bundle_exists[1] == "md5sum":
            raise ValueError(
                "A bundle with matching md5sum is already in system with a different name."
            )
        elif bundle_exists[1] == "both":
            print(
                "Warning - bundle {} has been declared previously - you are likely trying again as a result of a crash. Continuing".format(
                    pdf_fname
                )
            )
        else:
            raise RuntimeError("Should not be here: unexpected code path!")

    bundle_name, md5 = bundle_name_and_md5(pdf_fname)
    bundledir = Path("bundles") / "submittedHWByQ" / bundle_name
    make_required_directories(bundledir)

    print("Processing PDF {} to images".format(pdf_fname))
    scansToImages.processScans(pdf_fname, bundledir, not gamma, not extractbmp)

    print("Creating bundle for {} on server".format(pdf_fname))
    rval = sendPagesToServer.createNewBundle(bundle_name, md5, server, password)
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
        raise RuntimeError("Stopping, see above")

    # send the images to the server
    sendPagesToServer.uploadHWPages(
        bundle_name, skip_list, student_id, questions, server, password
    )
    # now archive the PDF
    scansToImages.archiveHWBundle(pdf_fname)


def processAllHWByQ(server, password, yes_flag):
    """Process and upload all HW by Q bundles in submission directory.

    Scan through the submittedHWByQ directory and process/upload
    each PDF in turn. User will be prompted for each unless the
    'yes_flag' is set.
    """

    submissions = defaultdict(list)
    for file_name in sorted(glob.glob(os.path.join("submittedHWByQ", "*.pdf"))):
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


def processMissing(server, password, yes_flag):
    """Replace missing questions with 'not submitted' pages

    Student may not upload pages for questions they don't answer. This function
    asks server for list of all missing hw-questions from all tests that have
    been used (but are not complete).

    For each test we check if any test-pages are present and skip if they are.

    For each remaining test we replace each missing question with a 'question not submitted' page. The user will be prompted in each case unless the 'yes_flag' is set.
    """
    from plom.scan import checkScanStatus

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


parser = argparse.ArgumentParser(
    description="Tools for dealing with student self-submitted scans.",
    epilog="""## Processing and uploading homework

    TODO: WRITE DOCS
    """,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
sub = parser.add_subparsers(dest="command")
#
spW = sub.add_parser(
    "submitted",
    help="status of student-submitted work, either local or on server",
    description="List student IDs and their submitted questions in the local"
    + " 'submittedHWByQ' directory or their work already uploaded the server.",
)
spP = sub.add_parser(
    "process",
    help="Process indicated PDF for one student and upload to server.",
    description="""
        Process a bundle of work (typically a PDF file) from one student.
        You must provide the student ID.  You must also indicate which
        question is in this bundle or that this is a "loose" bundle
        (including all questions or otherwise unstructured).
        Various flags control other aspects of how the bundle is
        processed.
    """,
)
spA = sub.add_parser(
    "allbyq",
    help="Process and upload all PDFs in 'submittedHWByQ' directory and upload to server",
    description="""
        Process and upload all PDFs in 'submittedHWByQ' directory.
        Look at the `q` in `foo_bar.12345678.q.pdf` to determine which
        question.  Upload to server.
    """,
)
spM = sub.add_parser(
    "missing",
    help="Replace missing answers with 'not submitted' pages.",
)
spS = sub.add_parser("status", help="Get scanning status report from server")
spC = sub.add_parser(
    "clear",
    help="Clear 'scanner' login",
    description="Clear 'scanner' login after a crash or other expected event.",
)
#

spW.add_argument(
    "-d",
    "--directory",
    action="store_true",
    help="Check submissions in local directory and not on server.",
)

spP.add_argument("hwPDF", action="store", help="PDF containing homework")
spP.add_argument("studentid", action="store", help="Student ID")
g = spP.add_mutually_exclusive_group(required=True)
g.add_argument(
    "-l",
    "--loose",
    action="store_true",
    help="Whether or not to upload file as loose pages.",
)
g.add_argument(
    "-q",
    "--question",
    nargs=1,
    metavar="N",
    action="store",
    help="""
        Which question(s) are answered in file.
        You can pass a single integer, in which case it should match
        the filename `foo_bar.<sid>.N.pdf` as documented elsewhere.
        You can also pass a list like `-q 1,2,3` in which case your
        filename must be of the form `foo_bar.<sid>._.pdf` (a single
        underscore).
        You can also pass the special string `-q all` which uploads
        this file to all questions.
    """,
)
g = spP.add_mutually_exclusive_group(required=False)
g.add_argument(
    "--gamma-shift",
    action="store_true",
    dest="gamma",
    help="""
        Apply white balancing to the scan, if the image format is
        lossless (PNG).
        By default, this gamma shift is NOT applied; this is because it
        may worsen some poor-quality scans with large shadow regions.
    """,
)
g.add_argument(
    "--no-gamma-shift",
    action="store_false",
    dest="gamma",
    help="Do not apply white balancing.",
)
g = spP.add_mutually_exclusive_group(required=False)
g.add_argument(
    "--extract-bitmaps",
    action="store_true",
    dest="extractbmp",
    help="""
        If a PDF page seems to contain exactly one bitmap image and
        nothing else, then extract that losslessly instead of rendering
        the page as a new PNG file.  This will typically give nicer
        images for the common scan case where pages are simply JPEG
        images.  But some care must be taken that the image is not
        annotated in any way and that no other markings appear on the
        page.
        As the algorithm to decide this is NOT YET IDEAL, this is
        currently OFF BY DEFAULT, but we anticipate it being the default
        in a future version.
    """,
)
g.add_argument(
    "--no-extract-bitmaps",
    action="store_false",
    dest="extractbmp",
    help="""
        Don't try to extract bitmaps; just render each page.  This is
        safer but not always ideal for image quality.
    """,
)

spA.add_argument(
    "-y",
    "--yes",
    action="store_true",
    help="Answer yes to prompts.",
)
spM.add_argument(
    "-y",
    "--yes",
    action="store_true",
    help="Answer yes to prompts.",
)


for x in (spW, spP, spA, spS, spC, spM):
    x.add_argument("-s", "--server", metavar="SERVER[:PORT]", action="store")
    x.add_argument("-w", "--password", type=str, help='for the "scanner" user')


def main():
    args = parser.parse_args()

    if not hasattr(args, "server") or not args.server:
        try:
            args.server = os.environ["PLOM_SERVER"]
        except KeyError:
            pass
    if not hasattr(args, "password") or not args.password:
        try:
            args.password = os.environ["PLOM_SCAN_PASSWORD"]
        except KeyError:
            pass

    if args.command == "submitted":
        whoDidWhat(args.server, args.password, args.directory)
    elif args.command == "process":
        if args.loose:
            processLooseScans(
                args.server,
                args.password,
                args.hwPDF,
                args.studentid,
                args.gamma,
                args.extractbmp,
            )
        else:
            questions = args.question[0]  # args passes '[q]' rather than just 'q'
            if questions == "all":
                N = get_number_of_questions(args.server, args.password)
                questions = list(range(1, N + 1))
            else:
                questions = [int(x) for x in questions.split(",")]
            processHWScans(
                args.server,
                args.password,
                args.hwPDF,
                args.studentid,
                questions,
                args.gamma,
                args.extractbmp,
            )
            # argparse makes args.question a list.
    elif args.command == "allbyq":
        # TODO: gamma and extractbmp?
        processAllHWByQ(args.server, args.password, args.yes)
    elif args.command == "missing":
        processMissing(args.server, args.password, args.yes)
    elif args.command == "status":
        scanStatus(args.server, args.password)
    elif args.command == "clear":
        clearLogin(args.server, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
