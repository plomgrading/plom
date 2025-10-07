#!/usr/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2025 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai
# Copyright (C) 2025 Aidan Murphy

r"""Upload papers and grades to Canvas from Plom.

Overview:

  1. Finish grading
  2. Reassemble papers.
  3. Copy this script into the current directory, and install:
    - tqdm
    - plom
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
     ./plom-push-to-canvas.py --help
     ```
  5. Run it again for real:
     ```
     ./plom-push-to-canvas.py --course xxxxxx \
                            --assignment xxxxxx \
                            --plom-server xxxxxx \
                            --plom-username xxxxx \
                            --no-section 2>&1 | tee push.log
     ```

This script traverses all papers in your Plom server with any
scanned student work - though it will ignore any papers that
haven't been ID'd.

Solutions and Reports cannot be uploaded yet.

Instructors and TAs can do this but in the past it would fail for
the "TA Grader" role: https://gitlab.com/plom/plom/-/issues/2338
"""


import argparse
import os
import sys
import random
import string
import time
from getpass import getpass
import requests
from tempfile import NamedTemporaryFile
from email.message import EmailMessage

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
from plom.messenger import PlomAdminMessenger
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomSeriousException,
    PlomNoPermission,
    PlomNoPaper,
    PlomNoServerSupportException,
)


# bump this a bit if you change this script
__script_version__ = "0.6.1"
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
            NOT IMPLEMENTED.
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
        help="""
            NOT IMPLEMENTED.
            Upload individualized student reports, in addition to reassembled papers
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
) -> list[canvasapi.course.Course]:
    """Get a list of the Canvas courses a particular user is teaching.

    Args:
        user: the canvas user to check

    Returns:
        A list of canvas course objects.
    """
    # TODO: this looks very inefficient, but I don't want to touch it.
    courses_teaching = []
    for course in user.get_courses():
        try:
            for enrollee in course.enrollments:
                if enrollee["user_id"] == user.id:
                    # observed types are "teacher", "ta", "student", "designer"
                    if enrollee["type"] in ["teacher", "ta"]:
                        courses_teaching += [course]
                    else:
                        continue

        except AttributeError:
            # OK for some reason a requester object is being included
            # as a course??????
            #
            # TODO: INvestigate further?
            # print(f"WARNING: At least one course is missing some expected attributes")
            pass

    return courses_teaching


def interactively_get_course_id(user):
    """Interactively get a course id from a user.

    Args:
        user: the Canvas user to whose course list to browse.

    Returns:
        The course id of the selected course.
    """
    courses_teaching = get_courses_teaching(user)
    print("\nAvailable courses:")
    print("  --------------------------------------------------------------------")
    for i, course in enumerate(courses_teaching):
        print(f"    {i}: {course.name}")

    course_chosen = False
    while not course_chosen:
        choice = input("\n  Choice [0-n]: ")
        if not (set(choice) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(choice) >= len(courses_teaching):
            print("Choice too large.")
        else:
            choice = int(choice)
            print(
                "  --------------------------------------------------------------------"
            )
            selection = courses_teaching[choice]
            print(f"  You selected {choice}: {selection.name}")
            confirmation = input("  Confirm choice? [y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                course_chosen = True
                course = selection
                break
    print(f'  Note: you can use "--course {course.id}" to reselect.\n')
    print("\n")
    return course.id


def get_course_by_id(
    course_number: int, user: canvasapi.current_user.CurrentUser
) -> canvasapi.course.Course | None:
    """Get a Canvas course object given course id and Canvas user object.

    Args:
        course_number: the id for the Canvas course.
        user: the Canvas user to authorise this.

    Returns:
        A Canvas course object if successful, or None if not.
    """
    course_list = get_courses_teaching(user)
    for course in course_list:
        if course_number == course.id:
            return course
    print(
        f"course id: {course_number} doesn't match any course in user's teaching list:"
        f"{course_list}."
    )
    time.sleep(1)
    return None


def get_canvas_course_section_by_id(
    course: canvasapi.course.Course, section_id: int
) -> canvasapi.section.Section | None:
    """Get a Canvas section object given a section id and Canvas course object.

    Args:
        course: the Canvas course object.
        section_id: the id for the desired section.

    Returns:
        A Canvas section object if successful, or None if not.
    """
    try:
        return course.get_section(section_id)
    except CanvasException as e:
        print(f'id "{section_id}" doesn\'t match any section in {course.name}: {e}')
        time.sleep(1)
        return None


def interactively_get_course_section_id(course: canvasapi.course.Course) -> int | None:
    """Choose a section from a menu.

    Args:
        course: a canvas course object. Sections from this course will be displayed.

    Returns:
        None or a section id.
    """
    print(f"\nSelect a Section from {course}.\n")
    print("  Available Sections:")
    print("  --------------------------------------------------------------------")

    sections = list(course.get_sections())
    i = 0
    print(
        f"    {i}: Do not choose a section (None) (Probably the right choice; read the help)"
    )
    i += 1
    for section in sections:
        print(f"    {i}: {section.name} ({section.id})")
        i += 1

    while True:
        choice = input("\n  Choice [0-n]: ")
        if not (set(choice) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(choice) >= len(sections) + 1:
            print("Choice too large.")
        else:
            choice = int(choice)
            print(
                "  --------------------------------------------------------------------"
            )
            if choice == 0:
                section = None
                print(f"  You selected {choice}: None")
            else:
                section = sections[choice - 1]
                print(f"  You selected {choice}: {section.name} ({section.id})")
            confirmation = input("  Confirm choice? [y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                print("\n")
                return section if section is None else section.id


def interactively_get_canvas_assignment_id(course: canvasapi.course.Course) -> int:
    """Choose an assignment from a menu.

    Args:
        course: a canvas course object. Assignments from this course will be displayed.

    Returns:
        An assignment id.
    """
    print(f"\nSelect an assignment for {course}.\n")
    print("  Available assignments:")
    print("  --------------------------------------------------------------------")

    assignments = list(course.get_assignments())
    for i, assignment in enumerate(assignments):
        print(f"    {i}: {assignment.name}")

    assignment_chosen = False
    while not assignment_chosen:
        choice = input("\n  Choice [0-n]: ")
        if not (set(choice) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(choice) >= len(assignments):
            print("Choice too large.")
        else:
            choice = int(choice)
            print(
                "  --------------------------------------------------------------------"
            )
            selection = assignments[choice]
            print(f"  You selected {choice}: {selection.name}")
            confirmation = input("  Confirm choice? [y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                assignment_chosen = True
                assignment = selection
    print(f'  Note: you can use "--assignment {assignment.id}" to reselect.\n')
    print("\n")
    return assignment.id


def get_canvas_assignment_by_id(
    course: canvasapi.course.Course, assignment_id: int
) -> canvasapi.assignment.Assignment | None:
    """Get a Canvas assignment object given an assignment id and Canvas course object.

    Args:
        course: the Canvas course object.
        assignment_id: the id of the desired assignment.

    Returns:
        A Canvas assignment object if successful, or None if not.
    """
    try:
        return course.get_assignment(assignment_id)
    except CanvasException:
        print(
            'id "{assignment_id}" doesn\'t match any assignment in {course.name}: {e}'
        )
        time.sleep(1)
        return None


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


###########################################################
###########################################################
# functions to interact with a Plom server


def get_plom_marks(msgr: PlomAdminMessenger) -> dict:
    """Get a list of information about exam papers on the server.

    More specifically this contains info about student marks and IDs.

    Returns:
        A dict of information keyed by the paper number it corresponds to.
    """
    if msgr.is_server_api_less_than(113):
        raise PlomNoServerSupportException(
            "Server too old: does not support getting plom marks"
        )

    with msgr.SRmutex:
        try:
            response = msgr.get_auth("/REP/spreadsheet")
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None


def restructure_plom_marks_dict(plom_marks_dict: dict) -> dict[int, dict[str, int]]:
    """Change the key on the Plom marks dicts to student number.

    This function will remove any papers with warnings attached (for example,
    in 0.19.2 this means the paper isn't completely marked, or hasn't been ID'd).

    Returns:
        A dict of exam marks keyed by student ids.
    """
    simplified_dict = {}
    # we won't attempt to push papers on the discard list to Canvas
    discard_list = []
    for key, value in plom_marks_dict.items():
        if PLOM_WARNINGS in value.keys():
            discard_list.append(value)
            continue

        simplified_dict[value[PLOM_STUDENT_ID]] = value

    # TODO: the discard list currently includes papers without any work attached!
    if discard_list:
        print("Some papers cannot be processed for push to Canvas:")
        print(tabulate(discard_list, headers="keys"))
        print(f"This script will not push these {len(discard_list)} results to Canvas,")
        confirmation = input("proceed? [y/n] ")
        if confirmation not in ["", "y", "Y", "\n"]:
            print("CANCELLED")
            sys.exit(0)

    return simplified_dict


def get_plom_reassembled(
    msgr, papernum: int, memfile: NamedTemporaryFile
) -> NamedTemporaryFile:
    """Download a reassembled PDF file from the Plom server.

    This is a rewrite of a native PlomAdminMessenger function.
    The intention is to leave file i/o and cleanup to python, rather
    than manage it ourselves.

    Args:
        msgr: A PlomAdminMessenger instance.
        papernum: the paper number of the paper to fetch.
        memfile: a reference to a NamedTemporaryFile. It must be
            opened with write permissions in **byte** mode.

    Returns:
        A reference to the NamedTemporaryFile passed in. It should now
        contain the reassembled exam paper specified by papernum.
    """
    if msgr.is_server_api_less_than(113):
        raise PlomNoServerSupportException(
            "Server too old: API does not support getting reassembled papers"
        )

    with msgr.SRmutex:
        try:
            response = msgr.get_auth(
                f"/api/beta/finish/reassembled/{papernum}", stream=True
            )
            response.raise_for_status()
            # https://stackoverflow.com/questions/31804799/how-to-get-pdf-filename-with-python-requests
            msg = EmailMessage()
            msg["Content-Disposition"] = response.headers.get("Content-Disposition")
            filename = msg.get_filename()
            assert filename is not None

            memfile.name = msg.get_filename()
            for chunk in response.iter_content(chunk_size=8192):
                memfile.write(chunk)

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 403:
                raise PlomNoPermission(response.reason) from None
            if response.status_code == 404:
                raise PlomNoPaper(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None


###########################################################


def main():
    args = get_parser().parse_args()

    unsupported_options = [args.solutions, args.reports]
    if any(unsupported_options):
        print(
            'You\'ve selected an unsupported option (probably "--solutions" or "--reports"), '
            "exiting."
        )
        sys.exit(1)

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError as e:
        print(f'"dotenv" not installed, cannot read .env file: {e}')

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
            canvas_course_section = get_canvas_course_section_by_id(
                canvas_course, args.section
            )
            print(f"({canvas_course_section}) " + CHECKMARK)

    if not args.assignment:
        args.assignment = interactively_get_canvas_assignment_id(canvas_course)
    print("Getting Canvas assignment...", end="")
    canvas_assignment = get_canvas_assignment_by_id(canvas_course, args.assignment)
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
    student_marks = restructure_plom_marks_dict(get_plom_marks(plom_messenger))
    print(f"Plom marks retrieved (for {len(student_marks)} examinees).")

    # put canvas submissions in a dict for fast recall
    # this dict is keyed by *canvas id* not student id
    raw_submissions = canvas_assignment.get_submissions()
    canvas_submissions = {}
    for submission in raw_submissions:
        canvas_submissions.update({submission.user_id: submission})

    # get canvas conversion dict - student id to canvas id
    if canvas_course_section:
        canvas_ids = get_canvas_id_dict(canvas_course_section)
    else:
        canvas_ids = get_canvas_id_dict(canvas_course)

    if args.dry_run:
        successes = []
    canvas_absences = []
    canvas_timeouts = []
    plom_timeouts = []
    for _, exam_dict in tqdm(student_marks.items()):
        paper_number = exam_dict[PLOM_PAPERNUM]
        score = exam_dict[PLOM_MARKS]
        student_id = exam_dict[PLOM_STUDENT_ID]
        student_name = exam_dict[PLOM_STUDENT_NAME]
        try:
            student_canvas_id = canvas_ids[student_id]
            # if the student has a Canvas id, this next line should never fail
            # but it did in testing (note sure how to reproduce).
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
                with NamedTemporaryFile("wb+") as f:
                    try:
                        get_plom_reassembled(plom_messenger, paper_number, f)
                        f.seek(0)
                    except (
                        PlomAuthenticationException,
                        PlomNoPermission,
                        PlomNoPaper,
                        PlomSeriousException,
                    ) as e:
                        print(e)
                        plom_timeouts.append(
                            {
                                "paper_number": paper_number,
                                "student_id": student_id,
                                "error": e,
                            }
                        )
                    successes.append(
                        {
                            "file/mark": f.name,
                            "student_id": student_id,
                            "student_name": student_name,
                            "student_canvas_id": student_canvas_id,
                        }
                    )
            if args.post_grades:
                successes.append(
                    {
                        "file/mark": score,
                        "student_id": student_id,
                        "student_name": student_name,
                        "student_canvas_id": student_canvas_id,
                    }
                )
            # UNIMPLEMENTED - no Plom API yet
            if args.reports:
                pass
            # UNIMPLEMENTED - no Plom API yet
            if args.solutions:
                pass
            continue

        # no real multithreading in python, so order doesn't really matter here
        if args.papers:
            with NamedTemporaryFile("wb+") as f:
                try:
                    get_plom_reassembled(plom_messenger, paper_number, f)
                    f.seek(0)
                    student_canvas_submission.upload_comment(f)
                except (
                    PlomAuthenticationException,
                    PlomNoPermission,
                    PlomNoPaper,
                    PlomSeriousException,
                ) as e:
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
            time.sleep(random.uniform(0.1, 0.3))

        if args.post_grades:
            try:
                student_canvas_submission.edit(submission={"posted_grade": score})
            except CanvasException as e:
                print(e)
                canvas_timeouts.append(
                    {
                        "paper_number": paper_number,
                        "student_id": student_id,
                        "error": f"{e}\n mark {score} couldn't be uploaded.",
                    }
                )
            time.sleep(random.uniform(0.1, 0.3))

        # no Plom API for this
        if args.solutions:
            pass

        # no Plom API for this
        if args.reports:
            pass
    print("\n")

    if plom_timeouts:
        print("FAILED DOWNLOADS FROM PLOM")
        print(tabulate(plom_timeouts, headers="keys"))
        print("\n\n")

    if canvas_absences:
        print("STUDENTS ABSENT FROM CANVAS")
        print(tabulate(canvas_absences, headers="keys"))
        print("\n\n")

    if canvas_timeouts:
        print("FAILED UPLOADS TO CANVAS")
        print(tabulate(canvas_timeouts, headers="keys"))
        print("\n\n")

    if args.dry_run:
        print("These items would've been uploaded to Canvas:")
        print(tabulate(successes, headers="keys"))
        print("\n\n")


if __name__ == "__main__":
    main()
