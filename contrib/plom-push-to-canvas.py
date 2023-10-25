#!/usr/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai

"""Upload reassembled Plom papers and grades to Canvas.

Overview:

  1. Finish grading
  2. Run `plom-finish csv` and `plom-finish reassemble`.
  3. Copy this script into the current directory.
  4. Run this script and follow the interactive menus:
     ```
     ./plom-push-to-canvas.py --dry-run
     ```
     It will output what would be uploaded.
  5. Note that you can provide command line arguments and/or
     set environment variables to avoid the interactive prompts:
     ```
     ./plom-push-to-canvas.py --help
     ```
  6. Run it again for real:
     ```
     ./plom-push-to-canvas.py --course xxxxxx --assignment xxxxxxx --no-section 2>&1 | tee push.log
     ```

This script traverses the files in `reassembled/` directory
and tries to upload them.  It takes the corresponding grades
from `marks.csv`.  There can be grades in `marks.csv` for which
there is no reassembled file in `reassembled/`: these are ignored.

Solutions can also be uploaded.  Again, only solutions that
correspond to an actual reassembled paper will be uploaded.

Instructors and TAs can do this but in the past it would fail for
the "TA Grader" role: https://gitlab.com/plom/plom/-/issues/2338
"""

import argparse
import os
from pathlib import Path
import random
import string
import time
from textwrap import dedent

from canvasapi.exceptions import CanvasException
from canvasapi import __version__ as __canvasapi_version__
import pandas
from tqdm import tqdm

from plom import __version__ as __plom_version__
from plom.canvas import __DEFAULT_CANVAS_API_URL__
from plom.canvas import (
    canvas_login,
    download_classlist,
    get_assignment_by_id_number,
    get_conversion_table,
    get_course_by_id_number,
    get_section_by_id_number,
    get_sis_id_to_canvas_id_table,
    get_student_list,
    interactively_get_assignment,
    interactively_get_course,
    interactively_get_section,
)


# bump this a bit if you change this script
__script_version__ = "0.2.1"


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
parser.add_argument(
    "--version",
    action="version",
    version=f"%(prog)s {__script_version__} (using Plom version {__plom_version__}, "
    f"and canvasapi package version {__canvasapi_version__})",
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
    help="Perform a dry-run without writing grades or uploading files.",
)
parser.add_argument(
    "--course",
    type=int,
    metavar="N",
    action="store",
    help="""
        Specify a Canvas course ID (an integer N).
        Interactively prompt from a list if omitted.
    """,
)
parser.add_argument(
    "--no-section",
    action="store_true",
    help="""
        Don't use section information from Canvas.
        In this case we will take the classlist directly from the
        course.
        In most cases, this is probably what you want UNLESS you have
        the same student in multiple sections (causing duplicates in
        the classlist, leading to problems).
    """,
)
parser.add_argument(
    "--section",
    type=int,
    metavar="N",
    action="store",
    help="""
        Specify a Canvas section ID (an integer N).
        If neither this nor "no-section" is specified then the script
        will interactively prompt from a list.
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
    if section:
        print("  Getting student list from Section...")
        student_list = get_student_list(section)
    else:
        print("  Getting student list from Course...")
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
        # the student number is whatever is after the last underscore
        sis_id = pdf.stem.split("_")[-1]
        # rebuild the stuff before the last underscore
        basename = "_".join(pdf.stem.split("_")[0:-1])
        assert len(sis_id) == 8, f"sis_id {sis_id} did not have 8 digits"
        assert set(sis_id) <= set(string.digits), f"sis_id {sis_id} had non-digit chars"
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
            # stuff "solutions" into filename, b/w base and SID
            soln_pdf = soln_dir / f"{basename}_solutions_{sis_id}.pdf"
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
        time.sleep(random.uniform(0.1, 0.2))
        if args.solutions and soln_pdf:
            try:
                sub.upload_comment(soln_pdf)
            except CanvasException as e:
                print(e)
                timeouts.append((soln_pdf.name, sis_id, name))
            time.sleep(random.uniform(0.1, 0.2))
        try:
            sub.edit(submission={"posted_grade": mark})
        except CanvasException as e:
            print(e)
            timeouts.append((mark, sis_id, name))
        time.sleep(random.uniform(0.1, 0.2))

    print(
        dedent(
            """

            ## Viewing the PDF files as an instructor

            Because of a Canvas bug, you (an instructor) may not be able to see these
            attachments directly in Canvas -> Grades.  There are two workarounds noted
            in https://github.com/instructure/canvas-lms/issues/1886
            (Students have no such problem; they will be able to see the attachment).
            """
        )
    )

    if args.dry_run:
        print("Done with DRY-RUN.  The following data would have been uploaded:")
        print("")
        print("    sis_id    student name       filename/mark")
        print("    --------------------------------------------")
        # note dry_run co-ops the timeout structure
        for thing, sis_id, name in timeouts:
            print(f"    {sis_id}  {name} \t {thing}")

    elif timeouts:
        print(f"Done, but there were {len(timeouts)} timeouts:")
        print("")
        print("    sis_id    student name       filename/mark")
        print("    --------------------------------------------")
        for thing, sis_id, name in timeouts:
            print(f"    {sis_id} {name} \t {thing}")
        print("  These should be uploaded manually, or rerun with only")
        print("  the failures placed in reassembled/")

    else:
        print("Done!  And there were no timeouts.")
