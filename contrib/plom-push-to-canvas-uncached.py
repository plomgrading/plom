#!/usr/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2025 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai
# Copyright (C) 2023 Laurent Mackay
# Copyright (C) 2025-2026 Aidan Murphy

r"""Upload papers and grades to Canvas from Plom.

Overview:

  1. Finish grading
  2. Reassemble papers.
  3. Copy this script into the current directory, and install:
    - tqdm
    - canvasapi
    - exif
    - plom   (TODO: maybe it even works with `pip install --no-deps plom`)
    - tabulate
    - python-dotenv (optional)
  4. Run this script and follow the interactive menus:
     ```
     ./plom-push-to-canvas-uncached.py --dry-run
     ```
     It will output what would be uploaded.
     Note that you can provide command line arguments and/or
     set environment variables to avoid the interactive prompts:
     ```
     ./plom-push-to-canvas-uncached.py --help
     ```
  5. Run it again for real:
     ```
     ./plom-push-to-canvas-uncached.py --course xxxxxx \
                            --assignment xxxxxx \
                            --plom-server xxxxxx \
                            --plom-username xxxxx \
                            --no-section 2>&1 | tee push.log
     ```

This script traverses all identified and marked papers in your Plom
server. It will ignore exams that are unidentified and/or unmarked.

Solutions and Reports cannot be uploaded yet.

Instructors and TAs can do this but in the past it would fail for
the "TA Grader" role: https://gitlab.com/plom/plom/-/issues/2338

Additional instructions for mastery/rubric-based grading:
    Populate your Canvas assignment with the (LO) rubrics before running
    the script.
    Include the "--rubrics" option in the invocation and follow
    the prompts.
"""

import argparse
import os
import sys
import random
import string
import time
from datetime import datetime, timezone
from getpass import getpass
from typing import Any

from tabulate import tabulate
from tqdm import tqdm

import canvasapi
from canvasapi import Canvas
from canvasapi.exceptions import CanvasException
from canvasapi import __version__ as __canvasapi_version__

from plom.common import (
    __version__ as __plom_version__,
    Default_Port,
)
from plom.cli import start_messenger
from plom.plom_exceptions import PlomException


# bump this a bit if you change this script
__script_version__ = "0.6.2"
__DEBUG__ = True

# These are the keys for the json returned by the Plom 'get spreadsheet' API call
PLOM_STUDENT_ID = "StudentID"
PLOM_STUDENT_NAME = "StudentName"
PLOM_MARKS = "Total"
PLOM_PAPERNUM = "PaperNumber"
PLOM_WARNINGS = "warnings"

# when calling course.get_enrollments(), the student objects returned
# will have student IDs stored in this attribute
CANVAS_STUDENT_ID = "sis_user_id"
__DEFAULT_CANVAS_API_URL__ = "https://canvas.ubc.ca"
# 2026-01-31T07:59:00Z
CANVAS_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

CHECKMARK = "\u2713"
CROSS = "\u274c"


def get_parser() -> argparse.ArgumentParser:
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
        "--api-key",
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
        help="Perform a dry-run without writing grades or uploading files to Canvas.",
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
        "--post-grades",
        action="store_true",
        default=True,
        help="""
            By default, we post grades for each student (as well as uploading
            the reassembled papers (default: on).
        """,
    )
    parser.add_argument(
        "--no-post-grades",
        dest="post_grades",
        action="store_false",
    )
    parser.add_argument(
        "--no-papers",
        dest="papers",
        action="store_false",
        help="""
            Don't push the reassembled papers.
        """,
    )
    parser.add_argument(
        "--solutions",
        action="store_true",
        default=False,
        help="""
            Upload individualized solutions, in addition to reassembled papers
            (default: off).
        """,
    )
    parser.add_argument(
        "--no-solutions",
        dest="solutions",
        action="store_false",
    )
    parser.add_argument(
        "--reports",
        action="store_true",
        default=False,
        help="""
            Upload individualized student reports, in addition to reassembled papers
            (default: off).
        """,
    )

    parser.add_argument(
        "--rubrics",
        action="store_true",
        default=False,
        help="""
            Upload the student's score on each question to Canvas rubrics.
            You will be prompted to select which Canvas rubric each Plom question
            (default: off).
        """,
    )

    parser.add_argument(
        "--plom-server",
        "-s",
        metavar="SERVER[:PORT]",
        help=f"""
            URL of server to contact. In SERVER, the protocol prefix is semi-optional:
            you can omit it and get https by default, or you can force http by including
            that explicitly. If [:PORT] is omitted, SERVER:{Default_Port} will be used.
            The environment variable PLOM_SERVER will be used if --plom-server is not given.
        """,
    )
    parser.add_argument(
        "-u",
        "--plom-username",
        type=str,
        help="""
            Also checks the environment variable PLOM_USERNAME.
        """,
    )
    parser.add_argument(
        "-w",
        "--plom-password",
        type=str,
        help="""
            Also checks the environment variable PLOM_PASSWORD.
        """,
    )

    return parser


def get_interactively_from_dict(choices: dict, *, prompt="Select one:"):
    """Ask user to pick a key, return the value."""
    print(f"\n{prompt}")
    print("  --------------------------------------------------------------------")

    for i, key in enumerate(choices.keys()):
        print(f"    {i}: {key}")

    key_chosen = False
    while not key_chosen:
        user_input = input("\n  Enter [0-n]: ")
        if not (set(user_input) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(user_input) >= len(choices.keys()):
            print("Choice too large.")
        else:
            user_input = int(user_input)
            print(
                "  --------------------------------------------------------------------"
            )
            selection = list(choices.keys())[user_input]
            print(f"  You selected {user_input}: {selection}")
            confirmation = input("  Confirm choice? [Y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                key_chosen = True

    return choices[selection]


###########################################################
# A suite of functions to get Canvas related stuff


def canvas_login(
    api_key: str, api_url: str | None = None, *, max_attempts: int = 3
) -> canvasapi.current_user.CurrentUser | None:
    """Login to a Canvas server using an API key.

    Args:
        api_url: the Canvas server to login to, uses a default if omitted.
        api_key: the Canvas API key.

    Keyword Args:
        max_attempts: if the credentials fail to authenticate,
            try again until they fail this many times.

    Returns:
        The user referenced by the given API key if successful, or None if not.
    """
    if not api_url:
        api_url = __DEFAULT_CANVAS_API_URL__

    count = 0
    while count < max_attempts:
        try:
            return Canvas(api_url, api_key).get_current_user()
        except CanvasException:
            count += 1
    # after max_attempts failures, assume issue with input credentials
    print("Couldn't authenticate with provided API key and api url")
    return None


def get_courses_teaching(
    user: canvasapi.current_user.CurrentUser,
    *,
    prune_inactive: bool = True,
) -> list[canvasapi.course.Course]:
    """Get a list of the Canvas courses a particular user is teaching.

    Args:
        user: the canvas user to check

    Keyword Args:
        prune_inactive: attempt to remove courses which seem inactive.
            Practices will vary by institution, you may need to turn this off.

    Returns:
        A list of canvas course objects.
    """
    courses_teaching = []
    for course in user.get_courses():

        # FK: OK for some reason a requester object is being included
        # as a course??????
        # AM: I'm guessing these are courses with db info deleted

        if prune_inactive:
            # https://developerdocs.instructure.com/services/canvas/resources/courses#courses-api
            # if end date has passed, remove course from selection
            # getattr because UBC seems to be deleting some old course db data
            end_datetime = getattr(course, "end_at", None)
            if end_datetime:
                end_datetime = datetime.strptime(end_datetime, CANVAS_DATETIME_FORMAT)
                end_datetime = end_datetime.replace(tzinfo=timezone.utc)
                if end_datetime < datetime.now(timezone.utc):
                    continue

        enrollments = getattr(course, "enrollments", [])
        for enrollee in enrollments:
            # There must be a reason this is here...
            if enrollee["user_id"] != user.id:
                continue
            # observed types are "teacher", "ta", "student", "designer"
            if enrollee["type"] not in ["teacher", "ta"]:
                continue

            courses_teaching += [course]

    return courses_teaching


def interactively_get_course_id(user):
    """Interactively get a course id from a user.

    CAUTION: this assumes each course is uniquely named.
    Duplicates are discarded.

    Args:
        user: the Canvas user to whose course list to browse.

    Returns:
        The course id of the selected course.
    """
    course_name_id_dict = {
        course.name: course.id for course in get_courses_teaching(user)
    }
    course_id = get_interactively_from_dict(
        course_name_id_dict, prompt="Available courses:"
    )
    print(f'  Note: you can use "--course {course_id}" to reselect.\n')
    print("\n")
    return course_id


def get_course_by_id(
    course_number: int, user: canvasapi.current_user.CurrentUser
) -> canvasapi.course.Course | None:
    """Get a Canvas course object given course id and Canvas user object.

    Args:
        course_number: the id for the Canvas course.
        user: the Canvas user to authorise this.

    Returns:
        A Canvas course object if successful, raises a ValueError otherwise.
    """
    course_list = get_courses_teaching(user)
    for course in course_list:
        if course_number == course.id:
            return course
    raise ValueError(
        f"course id: {course_number} doesn't match any course in user's teaching list:"
        f"{course_list}."
    )


def interactively_get_course_section_id(course: canvasapi.course.Course) -> int | None:
    """Choose a section from a menu.

    CAUTION: this assumes each section is uniquely named.
    Duplicates are discarded.

    Args:
        course: a canvas course object. Sections from this course will be displayed.

    Returns:
        None or a section id.
    """
    section_name_id_dict = {
        "Do not choose a section (None) (Probably the right choice; read the help)": None
    }
    section_name_id_dict.update(
        {section.name: section.id for section in course.get_sections()}
    )
    section_id = get_interactively_from_dict(
        section_name_id_dict, prompt=f"Select a section from {course}:"
    )
    if section_id is None:
        print('  Note: you can use "--no-section" to reselect.\n')
    else:
        print(f'  Note: you can use "--section {section_id}" to reselect.\n')

    print("\n")
    return section_id


def interactively_get_canvas_assignment_id(course: canvasapi.course.Course) -> int:
    """Choose an assignment from a menu.

    CAUTION: this assumes each assignment is uniquely named.
    Duplicates are discarded.

    Args:
        course: a canvas course object. Assignments from this course will be displayed.

    Returns:
        An assignment id.
    """
    assignment_name_id_dict = {
        assignment.name: assignment.id for assignment in course.get_assignments()
    }
    assignment_id = get_interactively_from_dict(
        assignment_name_id_dict, prompt=f"Select an assignment from {course}:"
    )
    print(f'  Note: you can use "--assignment {assignment_id}" to reselect.\n')
    print("\n")
    return assignment_id


def get_canvas_id_dict(
    course_or_section: canvasapi.course.Course | canvasapi.section.Section,
) -> dict[str, int]:
    """Get a dictionary of student canvas IDs keyed by student ID.

    This assumes a 'student' has a StudentEnrolment role and a
    student ID which isn't None.
    """
    canvas_ids = {}
    enrollees = course_or_section.get_enrollments()

    # Student ID format will vary by institution
    # explicitly casting the student ID to string is intentional
    # Canvas ID should always be a number, so less concern there.
    for enrollee in enrollees:
        if enrollee.role != "StudentEnrollment":
            continue
        if getattr(enrollee, CANVAS_STUDENT_ID, None) is None:
            continue
        canvas_ids.update(
            {str(getattr(enrollee, CANVAS_STUDENT_ID)): enrollee.user["id"]}
        )

    return canvas_ids


def interactively_get_canvas_rubrics_dict(
    canvas_assignment: canvasapi.assignment.Assignment,
    plom_marks_list: list[dict[str, Any]],
) -> dict[str, dict[int, dict]]:
    """Get a dict of canvas rubric dicts to upload for each student.

    The Canvas rubrics are specific to a given Canvas assignment.

    Returns:
        A dict of rubric dicts keyed by student ID, it looks like this:
        {
            student_id: {
                rubric_id: {
                    "rating_id": rating_id,
                    "points": rubric_mark,
                },
                rubric_id: {
                    "rating_id": rating_id,
                    "points": rubric_mark,
                },
            },
            student_id: {...},
            student_id: {...},
        }
    """
    plom_question_list = []

    for key in plom_marks_list[0].keys():
        # in the plom spreadsheet, columns ending in "_mark" denote
        # scores per question
        assert isinstance(key, str)
        if key.endswith("_mark"):
            plom_question_list.append(key)

    # map plom questions to canvas rubrics
    rubric_selection_dict = {
        "None - this Plom question doesn't correspond to any rubrics": None
    }
    for rubric in canvas_assignment.rubric:
        rubric_selection_dict.update(
            {f"{rubric['description']} - {rubric['long_description']}": rubric}
        )

    plom_q_to_canvas_rubric = {}
    for plom_question in plom_question_list:
        prompt = f"Pick which Canvas rubric corresponds to the plom question '{plom_question.removesuffix('_mark')}'"
        rubric = get_interactively_from_dict(rubric_selection_dict, prompt=prompt)
        # we need the ID of each rubric score, so put in a conversion dict too
        if rubric:
            rubric["points_rating_conversion"] = {
                rating["points"]: rating["id"] for rating in rubric["ratings"]
            }
        plom_q_to_canvas_rubric[plom_question] = rubric

    # map student ID to canvas rubrics
    student_id_to_rubrics = {}
    for marks_dict in plom_marks_list:
        student_id = marks_dict[PLOM_STUDENT_ID]

        rubrics_dict = {}
        for plom_q in plom_question_list:
            canvas_rubric = plom_q_to_canvas_rubric[plom_q]
            # None means user said plom_q to be ignored
            if canvas_rubric is None:
                continue
            points = int(marks_dict[plom_q])
            rating_id = canvas_rubric["points_rating_conversion"][points]
            rubrics_dict[canvas_rubric["id"]] = {
                "rating_id": rating_id,
                "points": points,
            }

        student_id_to_rubrics[student_id] = rubrics_dict

    return student_id_to_rubrics


###########################################################
###########################################################
# functions to interact with a Plom server


def restructure_plom_marks(plom_marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Change the key on the Plom marks dicts to student number.

    **WARNING: sometimes requires user interaction.**
    This function will remove any papers with warnings attached.

    Returns:
        A list of dicts.
    """
    simplified_list = []
    # we won't attempt to push papers on the discard list to Canvas
    discard_list = []
    for mark_dict in plom_marks:
        # Oct. 8th - the distinction between None and "" is significant
        # None means the paper was ID'd as having a blank coverpage
        # "" means the paper hasn't been ID'd yet and we will implicitly discard it
        # Oct. 24th: the API now gives only those that are ID'd so this may not happen
        if mark_dict[PLOM_STUDENT_ID] == "":
            continue

        # Oct. 8th - we explicitly discard unmarked papers
        if mark_dict[PLOM_WARNINGS]:
            discard_list.append(mark_dict)
            continue

        simplified_list.append(mark_dict)

    if discard_list:
        print(f"{len(discard_list)} paper[s] cannot be processed for push to Canvas:")
        print(tabulate(discard_list, headers="keys"))
        print(f"This script will not push these {len(discard_list)} results to Canvas,")
        confirmation = input("proceed? [Y/n] ")
        if confirmation not in ["", "y", "Y", "\n"]:
            print("CANCELLED")
            sys.exit(0)

    return simplified_list


###########################################################


def main():
    args = get_parser().parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    if hasattr(args, "api_key"):
        args.api_key = args.api_key or os.environ.get("CANVAS_API_KEY")
    if hasattr(args, "api_key") and not args.api_key:
        args.api_key = input("Please enter an API key for Canvas: ")
    print("Checking Canvas API key... ", end="")
    canvas_user = canvas_login(args.api_key, getattr(args, "api_url", None))
    print(CHECKMARK)

    if not args.course:
        args.course = interactively_get_course_id(canvas_user)
    print("Getting Canvas course... ", end="")
    canvas_course = get_course_by_id(args.course, canvas_user)
    print(f"({canvas_course}) " + CHECKMARK)

    if args.no_section:
        canvas_course_section = None
    else:
        if not args.section:
            args.section = interactively_get_course_section_id(canvas_course)

        if args.section:
            print("Getting Canvas section... ", end="")
            canvas_course_section = canvas_course.get_section(args.section)
            print(f"({canvas_course_section}) " + CHECKMARK)
        # user interactively selected "no course section"
        else:
            canvas_course_section = None

    if not args.assignment:
        args.assignment = interactively_get_canvas_assignment_id(canvas_course)
    print("Getting Canvas assignment...", end="")
    canvas_assignment = canvas_course.get_assignment(args.assignment)
    print(f"({canvas_assignment}) " + CHECKMARK)

    print(
        f"  * Assignment is published: {CHECKMARK if canvas_assignment.published else CROSS}"
    )
    print(
        f'  * Assignment is "post_manually": {CHECKMARK if canvas_assignment.post_manually else CROSS}'
    )
    if not canvas_assignment.published or not canvas_assignment.post_manually:
        raise ValueError(
            "Assignment must be published and set to manually release grades: see "
            "https://plom.rtfd.io/en/latest/returning.html#return-via-canvas"
        )

    if hasattr(args, "plom_server"):
        args.plom_server = args.plom_server or os.environ.get("PLOM_SERVER")
    if hasattr(args, "plom_username"):
        args.plom_username = args.plom_username or os.environ.get("PLOM_USERNAME")
    if hasattr(args, "plom_password"):
        args.plom_password = args.plom_password or os.environ.get("PLOM_PASSWORD")

    if hasattr(args, "plom_server") and not args.plom_server:
        args.plom_server = input("plom server: ")
    if hasattr(args, "plom_username") and not args.plom_username:
        args.plom_username = input("plom username: ")
    if hasattr(args, "plom_password") and not args.plom_password:
        args.plom_password = getpass("plom password: ")

    print("Checking plom credentials...", end="")
    plom_messenger = start_messenger(
        args.plom_server, args.plom_username, args.plom_password
    )
    print(CHECKMARK)

    # iterate over this
    student_marks = restructure_plom_marks(plom_messenger.get_paper_marks())
    print(f"Plom marks retrieved (for {len(student_marks)} examinees).")

    # put canvas submissions in a dict for fast recall
    # this dict is keyed by *canvas id* not student id
    inclusions = []
    if args.rubrics:
        inclusions.append("rubric_assessment")  # magic string - see Canvas API
    raw_submissions = canvas_assignment.get_submissions(include=inclusions)
    canvas_submissions = {}
    for submission in raw_submissions:
        canvas_submissions.update({submission.user_id: submission})

    if args.rubrics:
        student_rubrics = interactively_get_canvas_rubrics_dict(
            canvas_assignment, student_marks
        )

    # get canvas conversion dict - student id to canvas id
    if canvas_course_section:
        canvas_ids = get_canvas_id_dict(canvas_course_section)
    else:
        canvas_ids = get_canvas_id_dict(canvas_course)

    successes = []
    count = 0
    canvas_absences = []
    canvas_timeouts = []
    plom_timeouts = []
    for exam_dict in tqdm(student_marks):
        paper_number = exam_dict[PLOM_PAPERNUM]
        score = exam_dict[PLOM_MARKS]
        student_id = exam_dict[PLOM_STUDENT_ID]
        student_name = exam_dict[PLOM_STUDENT_NAME]
        try:
            student_canvas_id = canvas_ids[student_id]
            # if the student has a Canvas id, this next line should never fail
            # but it did in testing (not sure how to reproduce).
            student_canvas_submission = canvas_submissions[student_canvas_id]
        except KeyError:
            print(
                f"Student {student_name} - {student_id} (paper #{paper_number})"
                " couldn't be found in your canvas course (or section if specified),"
                " skipping."
            )
            canvas_absences.append(
                {
                    "paper_number": paper_number,
                    "student_id": student_id,
                    "error": f"{student_name} couldn't be found on Canvas.",
                }
            )
            continue

        if args.dry_run:
            if args.papers:
                try:
                    file_info = plom_messenger.get_reassembled(paper_number)
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_canvas_id": student_canvas_id,
                        }
                    )
                except PlomException as e:
                    print(e)
                    plom_timeouts.append(
                        {
                            "paper_number": paper_number,
                            "student_id": student_id,
                            "error": e,
                        }
                    )
                finally:
                    if os.path.exists(file_info["filename"]):
                        os.remove(file_info["filename"])
            if args.post_grades or args.rubrics:
                successes.append(
                    {
                        "file/mark": score,
                        "student_id": student_id,
                        "student_name": student_name,
                        "student_canvas_id": student_canvas_id,
                    }
                )
            if args.reports:
                try:
                    file_info = plom_messenger.get_report(paper_number)
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_canvas_id": student_canvas_id,
                        }
                    )
                except PlomException as e:
                    print(e)
                    plom_timeouts.append(
                        {
                            "paper_number": paper_number,
                            "student_id": student_id,
                            "error": e,
                        }
                    )
                finally:
                    if os.path.exists(file_info["filename"]):
                        os.remove(file_info["filename"])
            if args.solutions:
                try:
                    file_info = plom_messenger.get_solution(paper_number)
                    successes.append(
                        {
                            "file/mark": file_info["filename"],
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_canvas_id": student_canvas_id,
                        }
                    )
                except PlomException as e:
                    print(e)
                    plom_timeouts.append(
                        {
                            "paper_number": paper_number,
                            "student_id": student_id,
                            "error": e,
                        }
                    )
            continue

        # no real parallelism in python, so order doesn't really matter here
        if args.papers:
            try:
                file_info = plom_messenger.get_reassembled(paper_number)
                student_canvas_submission.upload_comment(file_info["filename"])
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            # TODO: should look at the negative response from Canvas
            except CanvasException as e:
                print(e)
                canvas_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                if os.path.exists(file_info["filename"]):
                    os.remove(file_info["filename"])

            time.sleep(random.uniform(0.1, 0.3))

        if args.post_grades or args.rubrics:
            content_dict = {}
            stuff = ""
            if args.post_grades:
                content_dict["submission"] = {}
                content_dict["submission"]["posted_grade"] = score
                stuff += f", mark {score}"
            if args.rubrics:
                content_dict["rubric_assessment"] = student_rubrics[student_id]
                stuff += ", rubrics"

            try:
                student_canvas_submission.edit(**content_dict)
            except CanvasException as e:
                print(e)
                canvas_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": f"{e}\n {stuff} couldn't be uploaded.",
                    }
                )
            time.sleep(random.uniform(0.1, 0.3))

        if args.solutions:
            try:
                file_info = plom_messenger.get_solution(paper_number)
                student_canvas_submission.upload_comment(file_info["filename"])
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            # TODO: should look at the negative response from Canvas
            except CanvasException as e:
                print(e)
                canvas_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                if os.path.exists(file_info["filename"]):
                    os.remove(file_info["filename"])

            time.sleep(random.uniform(0.1, 0.3))

        if args.reports:
            try:
                file_info = plom_messenger.get_report(paper_number)
                student_canvas_submission.upload_comment(file_info["filename"])
            except PlomException as e:
                print(e)
                plom_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            # TODO: should look at the negative response from Canvas
            except CanvasException as e:
                print(e)
                canvas_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": e,
                    }
                )
            finally:
                if os.path.exists(file_info["filename"]):
                    os.remove(file_info["filename"])

            time.sleep(random.uniform(0.1, 0.3))

        count += 1
    print("\n")
    print(f"pushed {count} papers without issue\n")

    if plom_timeouts:
        print(f"{len(plom_timeouts)} FAILED DOWNLOADS FROM PLOM")
        print(tabulate(plom_timeouts, headers="keys"))
        print("\n\n")

    if canvas_absences:
        print(f"{len(canvas_absences)} STUDENTS ABSENT FROM CANVAS")
        print(tabulate(canvas_absences, headers="keys"))
        print("\n\n")

    if canvas_timeouts:
        print(f"{len(canvas_timeouts)} FAILED UPLOADS TO CANVAS")
        print(tabulate(canvas_timeouts, headers="keys"))
        print("\n\n")

    if args.dry_run:
        print("These items would've been uploaded to Canvas:")
        print(tabulate(successes, headers="keys"))
        print("\n\n")


if __name__ == "__main__":
    main()
