#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021 Colin B. Macdonald

"""Upload reassembled Plom papers and grades to Canvas.

Overview:

  1. Finish grading
  2. Run `plom-finish csv` and `plom-finish reassemble`.
  3. Create `api_secrets.py` containing:
     ```
     my_key = "11224~AABBCCDDEEFF..."
     ```
  4. Run this script.

This script traverses the files in `reassembled/` directory
and tries to upload them.  It takes the corresponding grades
from `marks.csv`.  There can be grades in `marks.csv` for which
there is no reassembled file in `reassembled/`: these are ignored.

Solutions can also be uploaded.  Again, only solutions that
correspond to an actual reassembled paper will be uploaded.
"""

import argparse
from pathlib import Path
import random
import string
import time

from canvasapi.exceptions import CanvasException
import pandas
from tqdm import tqdm

from plom import __version__
from plom.canvas import __DEFAULT_CANVAS_API_URL__
from plom.canvas import (
    canvas_login,
    download_classlist,
    get_assignment_by_id_number,
    get_conversion_table,
    get_course_by_id_number,
    get_sis_id_to_canvas_id_table,
    interactively_get_assignment,
    interactively_get_course,
)


def get_student_list(course):
    students = []
    for enrollee in course.get_enrollments():
        # TODO: See if we also need to check for active enrollment
        if enrollee.role == "StudentEnrollment":
            students += [enrollee]
    return students


def sis_id_to_student_dict(student_list):
    out_dict = {}
    for student in student_list:
        assert student.role == "StudentEnrollment"
        try:
            assert student.sis_user_id is not None
        except AssertionError:
            # print(student.user_id)
            pass
            # print(student.)
        out_dict[student.sis_user_id] = student
    return out_dict


def get_sis_id_to_sub_and_name_table(subs):
    # Why the heck is canvas so stupid about not associating student
    # IDs with student submissions
    conversion = get_conversion_table()

    sis_id_to_sub = {}
    for sub in subs:
        canvas_id = sub.user_id
        try:
            name, sis_id = conversion[str(canvas_id)]
            sis_id_to_sub[sis_id] = (sub, name)
        except KeyError:
            print(
                f"couldn't find student information associated with canvas id {canvas_id}..."
            )

    return sis_id_to_sub


def get_sis_id_to_marks():
    """A dictionary of the Student Number ("sis id") to total mark."""
    df = pandas.read_csv("marks.csv", dtype="object")
    return df.set_index("StudentID")["Total"].to_dict()
    # TODO: if specific types are needed
    # return {str(k): int(v) for k,v in d.items()}


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
    help="Perform a dry-run without writing grades or uploading files.",
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
parser.add_argument(
    "--solutions",
    action="store_true",
    default=True,
    help="""
        Upload individualized solutions as well as reassembled papers
        (default: on).
    """,
)
parser.add_argument(
    "--no-solutions",
    dest="solutions",
    action="store_false",
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

    print("\nChecking if you have run `plom-finish`...")
    print("  --------------------------------------------------------------------")
    if not Path("marks.csv").exists():
        raise ValueError('Missing "marks.csv": run `plom-finish csv`')
    print('  Found "marks.csv" file.')
    if not Path("reassembled").exists():
        raise ValueError('Missing "reassembled/": run `plom-finish reassemble`')
    print('  Found "reassembled/" directory.')

    if args.solutions:
        soln_dir = Path("solutions")
        if not soln_dir.exists():
            raise ValueError(
                f'Missing "{soln_dir}": run `plom-finish solutions` or pass `--no-solutions` to omit'
            )
        print(f'  Found "{soln_dir}" directory.')

    print("\nFetching data from canvas now...")
    print("  --------------------------------------------------------------------")
    print("  Getting student list...")
    student_list = get_student_list(course)
    print("    done.")
    print("  Getting canvasapi submission objects...")
    subs = assignment.get_submissions()
    print("    done.")

    print("  Getting another classlist and various conversion tables...")
    download_classlist(course)
    print("    done.")

    # Most of these conversion tables are fully irrelevant once we
    # test this code enough to be confident we can remove the
    # assertions down below
    print("  Constructing SIS_ID to student conversion table...")
    sis_id_to_students = sis_id_to_student_dict(student_list)
    print("    done.")

    print("  Constructing SIS_ID to canvasapi submission conversion table...")
    sis_id_to_sub_and_name = get_sis_id_to_sub_and_name_table(subs)
    print("    done.")

    print("  Constructing SIS_ID to canvasapi submission conversion table...")
    # We only need this second one for double-checking everything is
    # in order
    sis_id_to_canvas = get_sis_id_to_canvas_id_table()
    print("    done.")

    print("  Finally, getting SIS_ID to marks conversion table.")
    sis_id_to_marks = get_sis_id_to_marks()
    print("    done.")

    if args.dry_run:
        print("\n\nPushing grades and marked papers to Canvas [DRY-RUN]...")
    else:
        print("\n\nPushing grades and marked papers to Canvas...")
    print("  --------------------------------------------------------------------")
    timeouts = []
    for pdf in tqdm(Path("reassembled").glob("*.pdf")):
        sis_id = pdf.stem.split("_")[1]
        assert len(sis_id) == 8
        assert set(sis_id) <= set(string.digits)
        try:
            sub, name = sis_id_to_sub_and_name[sis_id]
            student = sis_id_to_students[sis_id]
            mark = sis_id_to_marks[sis_id]
        except KeyError:
            print(f"No student # {sis_id} in Canvas!")
            print("  Hopefully this is 1-1 w/ a prev canvas id error")
            print("  SKIPPING this paper and continuing")
            continue
        assert sub.user_id == student.user_id
        if args.solutions:
            soln_pdf = soln_dir / f"{pdf.stem.split('_')[0]}_solutions_{sis_id}.pdf"
            if not soln_pdf.exists():
                print(f"WARNING: Student #{sis_id} has no solutions: {soln_pdf}")
                soln_pdf = None

        # try:
        #     if sub.submission_comments:
        #         print(sub.submission_comments)
        #     else:
        #         print("missing")
        # except AttributeError:
        #     print("no")
        #     pass
        if args.dry_run:
            timeouts.append((pdf.name, sis_id, name))
            if args.solutions and soln_pdf:
                timeouts.append((soln_pdf.name, sis_id, name))
            timeouts.append((mark, sis_id, name))
            continue

        # TODO: should look at the return values
        # TODO: back off on canvasapi.exception.RateLimitExceeded?
        try:
            sub.upload_comment(pdf)
        except CanvasException as e:
            print(e)
            timeouts.append((pdf.name, sis_id, name))
        time.sleep(random.uniform(0.25, 0.5))
        if args.solutions and soln_pdf:
            try:
                sub.upload_comment(soln_pdf)
            except CanvasException as e:
                print(e)
                timeouts.append((soln_pdf.name, sis_id, name))
            time.sleep(random.uniform(0.25, 0.5))
        try:
            sub.edit(submission={"posted_grade": mark})
        except CanvasException as e:
            print(e)
            timeouts.append((mark, sis_id, name))
        time.sleep(random.uniform(0.25, 0.5))

    if args.dry_run:
        print("Done with DRY-RUN.  The following data would have been uploaded:")
    else:
        print(f"Done.  There were {len(timeouts)} timeouts:")

    print("    sis_id   student name     filename/mark")
    print("    --------------------------------------------")
    for thing, sis_id, name in timeouts:
        print(f"    {sis_id} {name} \t {thing}")
    if not args.dry_run:
        print("  These should be uploaded manually, or rerun with only")
        print("  the failures placed in reassembled/")
