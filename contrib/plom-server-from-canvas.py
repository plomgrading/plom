#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai
# Copyright (C) 2023 Philip Loewen

"""Build and populate a Plom server from a Canvas Assignment.

The goal is automate using Plom as an alternative to Canvas's
SpeedGrader.

This is very much *pre-alpha*: not ready for production use, use at
your own risk, no warranty, etc, etc.

1. Create a Canvas API key on the Canvas site, it looks something like;
   ```
   11224~AABBCCDDEEFF...
   ```
2. Run `python3 plom-server-from-canvas.py`
3. Follow prompts.
4. Go the directory you created and run `plom-server launch`.

Notes:
  * If number of pages precisely matches number of questions then
    we do a 1-1 mapping onto questions.  Otherwise we push each
    page to all questions.  This could be made more configurable.

TODO:
  * needs to log instead of just discarding so much output
  * support an existing configured server in basedir: or fork
"""

import argparse
import csv
import os
from pathlib import Path
import random
import string
import subprocess
from textwrap import dedent
import time

import fitz
import PIL.Image
import requests
from tqdm import tqdm

from plom import __version__ as __plom_version__
from plom.misc_utils import working_directory
from plom.server import PlomServer
from plom.canvas import __DEFAULT_CANVAS_API_URL__
from plom.canvas import (
    canvas_login,
    download_classlist,
    get_assignment_by_id_number,
    get_conversion_table,
    get_course_by_id_number,
    get_section_by_id_number,
    interactively_get_assignment,
    interactively_get_course,
    interactively_get_section,
)
import plom.scan

# maybe temporary?
from plom.create import start_messenger


# bump this a bit if you change this script
__script_version__ = "0.4.0"


def get_short_name(long_name):
    """
    Generate the short name of assignment
    """
    short_name = ""
    push_letter = True
    while len(long_name):
        char, long_name = long_name[0], long_name[1:]
        if char in string.digits:
            push_letter = True
            short_name += char
        elif push_letter and char in string.ascii_letters:
            push_letter = False
            short_name += char.lower()
        elif char == " ":
            push_letter = True
        else:
            continue

    return short_name


def make_toml(assignment, marks, *, dur="."):
    """
    (assignment): a canvasapi assignment object
    """
    dur = Path(dur)
    longName = assignment.name

    name = get_short_name(longName)

    numberOfVersions = 1
    numberOfQuestions = len(marks)
    numberOfPages = len(marks) + 1

    numberToProduce = -1
    # note potentially useful
    # assignment.needs_grading_count, assignment.get_gradeable_students()

    toml = dedent(
        f"""
        # autogenerated by a script to pull from Canvas to Plom
        name = "{name}"
        longName = "{longName}"
        numberOfVersions = {numberOfVersions}
        numberOfPages = {numberOfPages}
        numberToProduce = {numberToProduce}
        numberOfQuestions = {numberOfQuestions}
        idPage = 1
        """
    ).lstrip()
    for i, mark in enumerate(marks):
        toml += dedent(
            f"""
            [question.{i + 1}]
            pages = [{i + 2}]
            mark = {mark}
            select = "fix"
            """
        ).lstrip()
    with open(dur / "canvasSpec.toml", "w") as f:
        f.write(toml)


def initialize(course, section, assignment, marks, *, server_dir="."):
    """
    Set up the test directory, get the classlist from canvas, make the
    .toml, etc
    """
    server_dir = Path(server_dir)
    server_dir.mkdir(exist_ok=True)

    print("\nGetting enrollment data from canvas and building `classlist.csv`...")
    download_classlist(course, section=section)

    print("Generating `canvasSpec.toml`...")
    make_toml(assignment, marks)

    with working_directory(server_dir):
        print("\nSwitched into test server directory.\n")
        print("Parsing `canvasSpec.toml`...")
        # TODO: we should replace all these with functions not cmdline?
        # TODO: capture and log all this output with capture_output=True?
        print("Autogenerating users...")
        subprocess.check_call(["plom-server", "users", "--auto", "12", "--numbered"])
        print("Processing userlist...")
        subprocess.check_call(["plom-server", "users", "userListRaw.csv"])
        print("Running `plom-server init`...")
        subprocess.check_call(["plom-server", "init"])

    print("Temporarily exporting manager password...")
    pwds = {}
    with open(server_dir / "userListRaw.csv", "r") as csvfile:
        for row in csv.reader(csvfile):
            pwds[row[0]] = row[1]
    os.environ["PLOM_MANAGER_PASSWORD"] = pwds["manager"]
    os.environ["PLOM_SCAN_PASSWORD"] = pwds["scanner"]
    print("")
    print("Secret stuff, probably don't just print it...")
    print(pwds["manager"])
    print(pwds["scanner"])
    print("")
    del pwds

    print("Launching plom server.")
    plom_server = PlomServer(basedir=server_dir)
    # TODO: consider suppressing output https://gitlab.com/plom/plom/-/issues/1586
    # Forest had popen(... ,stdout=subprocess.DEVNULL)
    print("Server *should* be running now")

    subprocess.check_call(["plom-create", "validatespec", "canvasSpec.toml"])
    subprocess.check_call(["plom-create", "uploadspec", "canvasSpec.toml"])

    # print("\n*** Here is the class list.")
    # subprocess.check_call(["cat", "classlist.csv"])

    # TODO: these had capture_output=True but this hides errors
    print("Building classlist...")
    build_class = subprocess.check_call(["plom-create", "class", "classlist.csv"])
    print("Building the database...")
    build_class = subprocess.check_call(["plom-create", "make-db"])

    return plom_server


def get_submissions(
    assignment, work_dir=".", name_by_info=True, dry_run=False, replace_existing=False
):
    """
    get the submission pdfs out of Canvas

    (name_by_info): Whether to make the filenames of the form ID_Last_First.pdf

    """
    work_dir = Path(work_dir)

    if name_by_info:
        print("Fetching conversion table...")
        conversion = get_conversion_table()

    tmp_downloads = work_dir / "upload" / "tmp_downloads"
    for_plom = work_dir / "upload" / "submittedHWByQ"

    tmp_downloads.mkdir(exist_ok=True, parents=True)
    for_plom.mkdir(exist_ok=True, parents=True)

    print("Fetching & preprocessing submissions...")
    subs = assignment.get_submissions()

    unsubmitted = []
    timeouts = []
    errors = []
    for sub in tqdm(subs):
        # Try to avoid overheating the canvas api (this is soooooo dumb lol)
        time.sleep(random.uniform(0.5, 1.0))
        if name_by_info:
            canvas_id = sub.user_id
            stud_name, stud_sis_id = conversion[str(canvas_id)]
            last_name, first_name = [name.strip() for name in stud_name.split(",")]
            sub_name = f"{last_name}_{first_name}.{stud_sis_id}._".replace(" ", "_")
        else:
            sub_name = f"{sub.user_id}"

        if (not replace_existing) and (for_plom / f"{sub_name}.pdf").exists():
            print(f"Skipping submission {sub_name} --- exists already")
            continue

        attachments = getattr(sub, "attachments", [])
        if not attachments:
            unsubmitted.append(sub)

        # Loop over all the attachments, save to disc, do some stitching
        # TODO: useful later to keep the student's original filename somewhere?
        attachment_filenames = []
        for i, obj in enumerate(attachments):
            print(f"*** Handling attachment number {i}")
            ctype = getattr(obj, "content-type")
            print(f"    Content type is {ctype}")
            if ctype == "null":
                # TODO: in what cases does this occur?
                continue
            elif ctype == "application/pdf":
                suffix = "pdf"
            elif ctype == "image/png":
                suffix = ".png"
            elif ctype == "image/jpg":
                suffix = ".jpg"
            elif ctype == "image/jpeg":
                suffix = ".jpeg"
            else:
                print(
                    f"unexpected content-type {ctype}: for now, appending to error list"
                )
                errors.append(sub)

            filename = tmp_downloads / f"{i:02}-{sub_name}.{suffix}"

            if dry_run:
                print(f"dry-run, but would download {filename.name}")
                filename.touch()
                continue

            time.sleep(random.uniform(0.5, 1.5))
            # TODO: try catch to a timeout/failed list?

            print("*** TODO: Investigate URL property of object more carefully")
            if not hasattr(obj, "url"):
                print("*** object has no 'url' property. Skipping it (?!)")
                # TODO: does this belong in the error list or not?  Under what
                # circumstances does it not have a url property?
                continue
            r = requests.get(obj.url)
            with open(filename, "wb") as f:
                f.write(r.content)

            if suffix != "pdf":
                # TODO: fitz can do this too
                img = PIL.Image.open(filename)
                img = img.convert("RGB")
                filename = filename.with_suffix(".pdf")
                img.save(filename)

            attachment_filenames.append(filename)

        final_name = for_plom / f"{sub_name}.pdf"
        if len(attachment_filenames) == 0:
            # TODO: what is this case, can it happen?
            pass
        elif len(attachment_filenames) == 1:
            attachment_filenames[0].rename(final_name)
        else:
            # TODO: stitching not ideal: prefer bundles from original files
            doc = fitz.Document()
            for f in attachment_filenames:
                try:
                    doc.insert_pdf(fitz.open(f))
                except RuntimeError:
                    print(f"We had problems with {sub} because of error on {f}")
                    errors.append(sub)
            # TODO: this could easily fail if we failed to the insertions above
            # TODO: anyway, like I said above, stitching not ideal
            doc.save(final_name)
            # Clean up temporary files (TODO: for now we leave them)
            # for x in attachment_filenames:
            #    x.unlink()

    for sub in unsubmitted:
        print(f"No submission from user_id {sub.user_id}")
    for sub in errors:
        print(f"Error getting submission from user_id {sub.user_id}")


def scan_submissions(
    num_questions,
    *,
    upload_dir,
    server_dir=None,
    server=None,
    scan_pwd=None,
    manager_pwd=None,
):
    """
    Apply `plom-scan` to all the pdfs we've just pulled from canvas

    TODO: delete server_dir: it should not know that, see below about API to get classlist.
    """
    upload_dir = Path(upload_dir)
    errors = []

    if not scan_pwd:
        scan_pwd = os.environ["PLOM_SCAN_PASSWORD"]
    if not manager_pwd:
        manager_pwd = os.environ["PLOM_MANAGER_PASSWORD"]
    if not server:
        server = os.environ["PLOM_SERVER"]

    if True:  # "PDLPATCH" in os.environ:
        # It seems like the student ID's from the classlist
        # have not yet been attached to numbered test papers
        # when we arrive at this point. Let's plan to make
        # such attachments just-in-time, and keep track of
        # which test papers we use with a list of Booleans.
        print("*** PDLPATCH: Creating a list of Booleans for test papers.")

        # We are also going to need a mapping from SID's to student names
        # and test numbers.
        # These don't seem to be in the database yet, either, so just
        # read the class list.
        sid2name = {}
        sid2test = {}
        # TODO: hardcoded, use API instead
        with open(server_dir / "specAndDatabase/classlist.csv", "r") as csvfile:
            reader = csv.DictReader(csvfile)
            classlist = list(reader)

        for k in range(len(classlist)):
            sid2name[classlist[k]["id"]] = classlist[k]["name"]
            sid2test[classlist[k]["id"]] = int(classlist[k]["paper_number"])

        # Ask the server for the largest paper number we might see.
        # Inferring this from len(sid2name) might work, but doing
        # the extra work might make this robust against incorrect assumptions.
        mm = start_messenger(server, manager_pwd)
        # TODO: later
        # mm.IDgetClasslist()
        infodict = mm.get_exam_info()
        mm.closeUser()
        mm.stop()
        PaperUsed = [False for _ in range(1, infodict["current_largest_paper_num"] + 1)]
        print(f"*** PDLPATCH: List PaperUsed has length {len(PaperUsed)}.")

    print("Applying `plom-hwscan` to pdfs...")
    for pdf in tqdm((upload_dir / "submittedHWByQ").glob("*.pdf")):
        # get 12345678 from blah_blah.blah_blah.12345678._.
        sid = pdf.stem.split(".")[-2]
        try:
            assert len(sid) == 8, "Student id has unexpected length, continuing"
        except AssertionError as e:
            errors.append((sid, e))
            continue

        # try to open pdf first, continue on error
        try:
            num_pages = len(fitz.open(pdf))
        except RuntimeError as e:
            print(f"Error processing student {sid} due to file error on {pdf}")
            errors.append((sid, e))
            continue

        if num_pages == num_questions:
            # If number of pages precisely matches number of questions then
            # do a 1-1 mapping...
            q = [[x] for x in range(1, num_questions + 1)]
        else:
            # ... otherwise push each page to all questionsa.
            q = [x for x in range(1, num_questions + 1)]
        # TODO: capture output and put it all in a log file?  (capture_output=True?)

        if True:  # "PDLPATCH" in os.environ:
            print("*** Found what looks like a legit PDF, as follows ...")
            print(f"    pdf:         {pdf}")
            print(f"    sid:         {sid}")
            print(f"    q:           {q}")

            studentname = sid2name[sid]
            print("*** PDLPATCH: Homebrew lookup suggests")
            print(f"    studentname: {studentname}")

            # Just-In-Time ID starts here.
            mm = start_messenger(server, manager_pwd)

            # Check if this SID is already associated with a test paper.
            # Here we are our own notes, not the database.
            # That's dubious.
            testnumber = sid2test[sid]
            if testnumber < 0:
                # Expected case - new SID, no prename
                testnumber = 1
                while PaperUsed[testnumber]:
                    testnumber += 1
                print(f"*** PDLPATCH: First unused test is number {testnumber}.")
                PaperUsed[testnumber] = True
                print(f"*** PDLPATCH: Reserving test {testnumber} for {studentname}.")
                sid2test[sid] = testnumber
                mm.pre_id_paper(testnumber, sid)
            else:
                if not PaperUsed[testnumber]:
                    print(
                        f"*** PDLPATCH: Classlist prescribes testnumber {testnumber}."
                    )
                    PaperUsed[testnumber] = True
                    mm.pre_id_paper(testnumber, sid)
                else:
                    print("*** PDLPATCH: EEK - not our first upload for this student.")
                    print("    MANUAL INVESTIGATION REQUIRED")

            mm.closeUser()
            mm.stop()

        # This broke until now
        plom.scan.processHWScans(
            pdf, sid, q, basedir=upload_dir, msgr=(server, scan_pwd)
        )
        # Now we can "lock-in" the IDing of it (optional, client can do later)
        mm = start_messenger(server, manager_pwd)
        try:
            mm.id_paper(testnumber, sid, studentname)
        finally:
            mm.closeUser()
            mm.stop()

    else:
        print(f"There was nothing in {upload_dir} for me to iterate over")

    for sid, err in errors:
        print(f"Error processing user_id {sid}: {str(err)}")

    # Clean up any missing submissions
    plom.scan.processMissing(msgr=(server, scan_pwd), yes_flag=True)


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--version",
    action="version",
    version=f"%(prog)s {__script_version__} (using Plom version {__plom_version__})",
)
parser.add_argument(
    "--api_url",
    type=str,
    default=__DEFAULT_CANVAS_API_URL__,
    action="store",
    help=f'URL for talking to Canvas, defaults to "{__DEFAULT_CANVAS_API_URL__}".',
)
parser.add_argument(
    "--api_key",
    type=str,
    action="store",
    help="""
        The API Key for talking to Canvas.
        You can instead set the environment variable CANVAS_API_KEY.
        If not specified by either mechanism, you will be prompted
        to enter it.
    """,
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Perform a dry-run, for example, don't download papers",
)
parser.add_argument(
    "--dir",
    type=str,
    action="store",
    help="The local directory for the Plom Server files (prompts if omitted).",
)
parser.add_argument(
    "--course",
    type=int,
    metavar="N",
    action="store",
    help="""
        Specify a Canvas Course ID (an integer N).
        Interactively prompt from a list if omitted.
    """,
)
parser.add_argument(
    "--section",
    type=int,
    metavar="N",
    action="store",
    help="""
        Specify a Canvas Section ID (an integer N).
        Interactively prompt from a list if omitted.
        Pass "--no-section" to not use Sections at all.
    """,
)
parser.add_argument(
    "--no-section",
    action="store_true",
    help="""
        Overwrites the --section flag to not use sections (and take the
        classlist directly from the Course).
    """,
)
parser.add_argument(
    "--assignment",
    type=int,
    metavar="M",
    action="store",
    help="""
        Specify a Canvas Assignment ID (an integer M).
        Interactively prompt from a list if omitted.
    """,
)
parser.add_argument(
    "--marks",
    type=str,
    metavar="LIST",
    action="store",
    help="""
        A comma-separated list of integers specifying the marks for
        each question.  This also specifies the number of questions.
        For example "5,10,4" means we have three questions worth 5,
        10 and 4 respectively.  If you use spaces after the commas,
        you'll need quotes around the list, as in `--marks "5, 10, 4"`.
    """,
)
parser.add_argument(
    "--no-init",
    action="store_false",
    dest="init",
    help="Do not initialize the plom server",
)
parser.add_argument(
    "--no-upload",
    action="store_false",
    dest="upload",
    help="Do not run submission-grabbing from Canvas and uploading to plom server",
)

if __name__ == "__main__":
    print("************************************************************")
    print("WARNING: this script in a work-in-progress, largely progress")
    print('and precious little "work"')
    print("************************************************************")
    args = parser.parse_args()
    if hasattr(args, "api_key"):
        args.api_key = args.api_key or os.environ.get("CANVAS_API_KEY")
        if not args.api_key:
            args.api_key = input("Please enter the API key for Canvas: ")

    user = canvas_login(args.api_url, args.api_key)

    if args.course is None:
        course = interactively_get_course(user)
        print(f'Note: you can use "--course {course.id}" to reselect.\n')
    else:
        course = get_course_by_id_number(args.course, user)
    print(f"Ok using course: {course}")

    if args.no_section:
        section = None
    elif args.section:
        section = get_section_by_id_number(course, args.section)
    else:
        section = interactively_get_section(course)
        if section is None:
            print('Note: you can use "--no-section" to omit selecting section.\n')
        else:
            print(f'Note: you can use "--section {section.id}" to reselect.\n')
    print(f"Ok using section: {section}")

    if args.assignment:
        assignment = get_assignment_by_id_number(course, args.assignment)
    else:
        assignment = interactively_get_assignment(course)
        print(f'Note: you can use "--assignment {assignment.id}" to reselect.\n')
    print(f"Ok downloading from Assignment: {assignment}")

    o_dir = os.getcwd()

    if args.dir is None:
        basedir = input("Name of dir to use for this assignment: ")
    else:
        basedir = args.dir
    basedir = Path(basedir)

    if basedir.is_dir():
        print(f'Using existing dir "{basedir}"')
        # TODO: ensure empty or warn if somethings exist?
    else:
        print(f'Creating dir "{basedir}"')
        basedir.mkdir(exist_ok=True)

    pp = assignment.points_possible
    print(f'\n"{assignment}" has "{pp}" points possible')
    if pp == 0 or int(pp) != pp:
        raise ValueError(
            "Points possible must be non-zero int: Plom supports only integer marking"
        )
    if args.marks is None:
        print(f"Do you want to split this total of {pp} over multiple questions?")
        args.marks = input('Enter a list for the marks per question, e.g., "5,10,3": ')
    args.marks = [int(x) for x in args.marks.split(",")]
    symsum = " + ".join(str(x) for x in args.marks)
    if sum(args.marks) != pp:
        raise ValueError(f"Total marks do not match Canvas: {symsum} =/= {pp}")
    print(f"Ok, using {len(args.marks)} questions with breakdown {symsum} = {pp}")
    del pp

    if args.init:
        print(f"Initializing a fresh plom server in {basedir}")
        plom_server = initialize(
            course, section, assignment, args.marks, server_dir=(basedir / "srv")
        )
    else:
        print(f"Using an already-initialize plom server in {basedir}")
        plom_server = PlomServer(basedir=basedir)

    if args.upload:
        print("\n\ngetting submissions from canvas...")
        get_submissions(assignment, dry_run=args.dry_run, work_dir=basedir)

        print("scanning submissions...")
        print(plom_server)
        print(type(plom_server))
        # TODO: hardcoded server hostname here, and remove server_dir
        scan_submissions(
            len(args.marks),
            server="localhost:41984",
            server_dir=(basedir / "srv"),
            upload_dir=(basedir / "upload"),
        )

    input("Press enter when you want to stop the server...")
    plom_server.stop()
    print("Server stopped, goodbye!")
