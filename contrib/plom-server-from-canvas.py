#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021 Colin B. Macdonald

"""Build and populate a Plom server from a Canvas Assignment.

The goal is automate using Plom as an alternative to Canvas's
SpeedGrader.

This is very much *pre-alpha*: not ready for production use, use at
your own risk, no warranty, etc, etc.

1. Create `api_secrets.py` containing
   ```
   my_key = "11224~AABBCCDDEEFF..."
   ```
2. Run `python plom-server-from-canvas.py`
   You will need the `aria2c` command-line downloader in addition
   to the usual Plom dependencies.
3. Follow prompts.
4. Go the directory you created and run `plom-server launch`.

TODO:
  * needs to log instead of just discarding so much output
"""

import argparse
import csv
import os
from pathlib import Path
import random
import string
import subprocess
import time

import fitz
import PIL
from tqdm import tqdm

from plom import __version__
from plom.server import PlomServer
from plom.canvas import __DEFAULT_CANVAS_API_URL__
from plom.canvas import (
    canvas_login,
    download_classlist,
    get_assignment_by_id_number,
    get_conversion_table,
    get_course_by_id_number,
    interactively_get_assignment,
    interactively_get_course,
)


def get_short_name(long_name):
    """"""
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


def get_toml(assignment, server_dir="."):
    """
    (assignment): a canvasapi assignment object
    """
    server_dir = Path(server_dir)
    longName = assignment.name

    name = get_short_name(longName)

    numberOfVersions = 1  # TODO: Make this not hardcoded
    numberOfPages = 20  # TODO: Make this not hardcoded

    numberToProduce = -1
    numberToName = -1
    # note potentially useful
    # assignment.needs_grading_count, assignment.get_gradeable_students()

    # What a beautiful wall of +='s
    toml = ""
    toml += f'name="{name}"\n'
    toml += f'longName="{longName}"\n'
    toml += f"numberOfVersions={numberOfVersions}\n"
    toml += f"numberOfPages={numberOfPages}\n"
    toml += f"numberToProduce={numberToProduce}\n"
    toml += f"numberToName={numberToName}\n"
    toml += "numberOfQuestions=1\n"
    toml += "[idPages]\npages=[1]\n"
    toml += "[doNotMark]\npages=[2]\n"
    toml += f"[question.1]\npages={list(range(3,numberOfPages+1))}\n"
    toml += (
        f"mark={int(assignment.points_possible) if assignment.points_possible else 1}\n"
    )
    if assignment.points_possible - int(assignment.points_possible) != 0:
        assert False  # OK this error needs to be handled more
        # intelligently in the future
    toml += 'select="fix"'

    with open(server_dir / "canvasSpec.toml", "w") as f:
        f.write(toml)


def initialize(course, assignment, server_dir="."):
    """
    Set up the test directory, get the classlist from canvas, make the
    .toml, etc
    """
    server_dir = Path(server_dir)
    server_dir.mkdir(exist_ok=True)

    print("\nGetting enrollment data from canvas and building `classlist.csv`...")
    download_classlist(course, server_dir=server_dir)

    print("Generating `canvasSpec.toml`...")
    get_toml(assignment, server_dir=server_dir)

    o_dir = os.getcwd()
    try:
        os.chdir(server_dir)
        print("\nSwitched into test server directory.\n")
        print("Parsing `canvasSpec.toml`...")
        subprocess.run(["plom-build", "parse", "canvasSpec.toml"], capture_output=True)
        print("Running `plom-server init`...")
        subprocess.run(["plom-server", "init"], capture_output=True)
        print("Autogenerating users...")
        subprocess.run(["plom-server", "users", "--auto", "1"], capture_output=True)
        print("Processing userlist...")
        subprocess.run(["plom-server", "users", "userListRaw.csv"], capture_output=True)
    finally:
        os.chdir(o_dir)

    print("Temporarily exporting manager password...")
    user_list = []
    with open(server_dir / "userListRaw.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            user_list += [row]
    os.environ["PLOM_MANAGER_PASSWORD"] = user_list[1][1]
    del user_list

    print("Launching plom server.")
    plom_server = PlomServer(basedir=server_dir)
    # TODO: consider suppressing output https://gitlab.com/plom/plom/-/issues/1586
    # Forest had popen(... ,stdout=subprocess.DEVNULL)
    print("Server *should* be running now")

    try:
        print("Building classlist...")
        build_class = subprocess.run(
            ["plom-build", "class", "classlist.csv"], capture_output=True
        )
        print("Building the database...")
        build_class = subprocess.run(
            ["plom-build", "make", "--no-pdf"], capture_output=True
        )
    finally:
        os.chdir(o_dir)

    return plom_server


def get_submissions(
    assignment, server_dir=".", name_by_info=True, dry_run=False, replace_existing=False
):
    """
    get the submission pdfs out of Canvas

    (name_by_info): Whether to make the filenames of the form ID_Last_First.pdf

    """
    server_dir = Path(server_dir)
    o_dir = os.getcwd()

    if name_by_info:
        print("Fetching conversion table...")
        conversion = get_conversion_table(server_dir=server_dir)

    os.chdir(server_dir)

    if not os.path.exists("upload"):
        os.mkdir("upload")

    os.chdir("upload")

    if not os.path.exists("submittedHWByQ"):
        os.mkdir("submittedHWByQ")

    os.chdir("submittedHWByQ")

    print("Moved into ./upload/submittedHWByQ")

    print("Fetching & preprocessing submissions...")
    subs = list(assignment.get_submissions())

    # TODO: Parallelize requests
    unsubmitted = []
    timeouts = []
    for sub in tqdm(subs):
        # Try to avoid overheating the canvas api (this is soooooo dumb lol)
        time.sleep(random.random())
        # TODO: is `aria2c` actually faster here lol??
        # time.sleep(random.uniform(0.5, 1.5))
        if name_by_info:
            canvas_id = sub.user_id
            stud_name, stud_sis_id = conversion[str(canvas_id)]
            last_name, first_name = [name.strip() for name in stud_name.split(",")]
            sub_name = f"{last_name}_{first_name}.{stud_sis_id}._.pdf".replace(" ", "_")
        else:
            sub_name = f"{sub.user_id}.pdf"

        if (not replace_existing) and (os.path.exists(sub_name)):
            # print(f"Skipping submission {sub_name} --- exists already")
            continue

        try:
            # If the student submitted multiple times, get _all_
            # the submissions.
            version = 0
            sub_subs = []
            for obj in sub.attachments:
                # sub-submission name --- prepend with a version
                # number to make stitching them together easier
                if type(obj) == dict:
                    # TODO: Test which of these cases are actually
                    # relevant
                    suffix = None
                    if obj["content-type"] == "null":
                        continue
                    elif obj["content-type"] == "application/pdf":
                        sub_sub_name = f"{version:02}-{sub_name}"
                    elif obj["content-type"] == "image/png":
                        suffix = ".png"
                        sub_sub_name = f"{version:02}-{sub_name}"[:-4] + suffix
                    elif obj["content-type"] == "image/jpg":
                        suffix = ".jpg"
                        sub_sub_name = f"{version:02}-{sub_name}"[:-4] + suffix
                    elif obj["content-type"] == "image/jpeg":
                        suffix = ".jpeg"
                        sub_sub_name = f"{version:02}-{sub_name}"[:-4] + suffix

                    version += 1

                    sub_url = obj["url"]
                    if not dry_run:
                        time.sleep(random.uniform(2.5, 6.5))
                        subprocess.run(
                            ["aria2c", sub_url, "-o", sub_sub_name, "-t", "240"],
                            capture_output=True,
                        )
                    else:
                        subprocess.run(
                            ["touch", sub_sub_name],
                            capture_output=True,
                        )

                    # subprocess.run(
                    #     ["curl", "-L", sub_url, "--output", sub_sub_name],
                    #     capture_output=True,
                    # )

                    if suffix is not None:
                        pdfname = f"{sub_sub_name}"[: -len(suffix)] + ".pdf"
                        if not dry_run:
                            img = PIL.Image.open(sub_sub_name)
                            img = img.convert("RGB")
                            img.save(pdfname)
                            sub_sub_name = pdfname
                        else:
                            subprocess.run(["touch", pdfname])

                    sub_subs += [sub_sub_name]

            if sub_subs and not dry_run:
                # Stitch together
                doc = fitz.Document()
                for sub_sub in sub_subs:
                    try:
                        to_insert = fitz.open(sub_sub)
                        doc.insert_pdf(to_insert)
                    except RuntimeError:
                        print(f"Could not find {sub_sub}.")
                        print(f"Current directory: {os.getcwd()}")
                        print(f"Contents:", os.listdir())

                doc.save(sub_name)
                # Clean up temporary files
                for sub_sub in sub_subs:
                    subprocess.run(["rm", sub_sub])
        except AttributeError:  # Catches if student didn't submit
            unsubmitted += [sub]
            continue

    for sub in unsubmitted:
        print(f"No submission from user_id {sub.user_id}")

    os.chdir(o_dir)


def scan_submissions(server_dir="."):
    """
    Apply `plom-scan` to all the pdfs we've just pulled from canvas
    """
    o_dir = os.getcwd()
    os.chdir(server_dir)

    user_list = []
    with open("userListRaw.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            user_list += [row]

    os.environ["PLOM_SCAN_PASSWORD"] = user_list[2][1]

    os.chdir("upload")

    print("Temporarily exporting scanner password...")

    # TODO: Parallelize here
    print("Applying `plom-hwscan` to pdfs...")
    pdfs = [f for f in os.listdir("submittedHWByQ") if ".pdf" == f[-4:]]
    for pdf in tqdm(pdfs):
        stud_id = pdf.split(".")[1]
        assert len(stud_id) == 8
        subprocess.run(
            ["plom-hwscan", "process", "submittedHWByQ/" + pdf, stud_id, "-q", "1"],
            capture_output=True,
        )

    # Clean up any missing submissions
    subprocess.run(
        ["plom-hwscan", "missing"],
        capture_output=True,
    )

    os.chdir(o_dir)


parser = argparse.ArgumentParser(
    description=__doc__.split("\n")[0],
    epilog="\n".join(__doc__.split("\n")[1:]),
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
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
        You can store this in a local file "api_secrets.py" as
        a string in a variable named "my_key".
        TODO: If blank, prompt for it?
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
    "--assignment",
    type=int,
    metavar="M",
    action="store",
    help="""
        Specify a Canvas Assignment ID (an integer M).
        Interactively prompt from a list if omitted.
    """,
)


if __name__ == "__main__":
    args = parser.parse_args()
    user = canvas_login(args.api_url, args.api_key)

    if args.course is None:
        course = interactively_get_course(user)
        print(f'Note: you can use "--course {course.id}" to reselect.\n')
    else:
        course = get_course_by_id_number(args.course, user)
    print(f"Ok using course: {course}")

    if args.assignment:
        assignment = get_assignment_by_id_number(course, args.assignment)
    else:
        assignment = interactively_get_assignment(user, course)
        print(f'Note: you can use "--assignment {assignment.id}" to reselect.\n')
    print(f"Ok uploading to Assignment: {assignment}")

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

    plom_server = initialize(course, assignment, server_dir=basedir)

    print("\n\ngetting submissions from canvas...")
    get_submissions(assignment, dry_run=args.dry_run, server_dir=basedir)

    print("scanning submissions...")
    scan_submissions(server_dir=basedir)

    input("Press enter when you want to stop the server...")
    plom_server.stop()
    print("Server stopped, goodbye!")
