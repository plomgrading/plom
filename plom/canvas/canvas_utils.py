# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2024 Colin B. Macdonald

"""Misc utils for interacting with Canvas."""

from __future__ import annotations

import csv
from pathlib import Path
import string
from warnings import warn
from typing import Any, Dict, Union

from canvasapi import Canvas

from plom.canvas import __DEFAULT_CANVAS_API_URL__


def get_student_list(course_or_section):
    """Get the list of students in a Course or a Section.

    Args:
        course (canvasapi.course.Course/canvasapi.section.Section):

    Returns:
        list: of `canvasapi.student.Student`.
    """
    students = []
    for enrollee in course_or_section.get_enrollments():
        # TODO: See if we also need to check for active enrollment
        if enrollee.role == "StudentEnrollment":
            students += [enrollee]
    return students


def download_classlist(course, *, section=None, workdir: Union[Path, str] = "."):
    """Download .csv of the classlist and various conversion tables.

    Args:
        course (canvasapi.course.Course): we will query for enrollment.

    Keyword Args:
        workdir (str/pathlib.Path): where to save the file.  Defaults
            to current working directory.
        section (None/canvasapi.section.Section): Which section should
            we take enrollment from?  If None (default), take all
            students directly from `course`.  Note at least in some cases
            omitting `section` can lead to duplicate students.

    Returns:
        None: But saves files.

    TODO: spreadsheet with entries of the form (student ID, student name)
    TODO: so is it the plom classlist or something else?

    TODO: this code is filled with comments/TODOs about collisions...

    Missing information doesn't reaaaaaaaaally matter to us so we'll
    just fill it in as needed.  That is a questionable statement; this
    function needs a serious review.
    """
    workdir = Path(workdir)
    if section:
        enrollments_raw = section.get_enrollments()
    else:
        enrollments_raw = course.get_enrollments()
    students = [_ for _ in enrollments_raw if _.role == "StudentEnrollment"]

    # FIXME: This should probably contain checks to make sure we get
    # no collisions.
    default_id = 0  # ? not sure how many digits this can be. I've seen 5-7
    default_sis_id = 0  # 8-digit number
    default_sis_login_id = 0  # 12-char jumble of letters and digits

    classlist = [
        ("Student", "ID", "SIS User ID", "SIS Login ID", "Section", "Student Number")
    ]

    conversion = [("Internal Canvas ID", "Student", "SIS User ID")]

    secnames: Dict[Any, Any] = {}

    for stud in students:
        stud_name, stud_id, stud_sis_id, stud_sis_login_id = (
            stud.user["sortable_name"],
            stud.id,
            stud.sis_user_id,
            stud.user["integration_id"],
        )

        internal_canvas_id = stud.user_id

        # In order to make defaults work, we have to construct the
        # list here in pieces, which is really inelegant and gross.

        # Can't do this with a for loop, sadly, because pass by
        # reference makes it hard to modify the default values.
        #
        # I say "can't" when really I mean "didn't"

        # FIXME: Treat collisions

        if (
            not stud_id
            or stud_id is None
            or (isinstance(stud_id, str) and stud_id in string.whitespace)
        ):
            stud_id = str(default_id)
            # 5-7 characters is what I've seen, so let's just go with 7
            stud_id = (7 - len(stud_id)) * "0" + stud_id
            default_id += 1

        if (
            not stud_sis_id
            or stud_sis_id is None
            or (isinstance(stud_sis_id, str) and stud_sis_id in string.whitespace)
        ):
            stud_sis_id = str(default_sis_id)
            # 8 characters is necessary for UBC ID
            stud_sis_id = (8 - len(stud_sis_id)) * "0" + stud_sis_id
            default_sis_id += 1

        if (
            not stud_sis_login_id
            or stud_sis_login_id is None
            or (
                isinstance(stud_sis_login_id, str)
                and stud_sis_login_id in string.whitespace
            )
        ):
            stud_sis_login_id = str(default_sis_login_id)
            stud_sis_login_id = (12 - len(stud_sis_login_id)) * "0" + stud_sis_login_id
            default_sis_login_id += 1

        # TODO: presumably this is just `section` when that is non-None?
        section_id = stud.course_section_id
        if not secnames.get(section_id):
            # caching section names
            sec = course.get_section(section_id)
            secnames[section_id] = sec.name

        # Add this information to the table we'll write out to the CSV
        classlist += [
            (
                stud_name,
                stud_id,
                stud_sis_id,
                stud_sis_login_id,
                secnames[section_id],
                stud_sis_id,
            )
        ]

        conversion += [(internal_canvas_id, stud_name, stud_sis_id)]

    with open(workdir / "classlist.csv", "w", newline="\n") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(classlist)

    with open(workdir / "conversion.csv", "w", newline="\n") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(conversion)


def get_conversion_table(*, workdir: Union[Path, str] = "."):
    """A mapping Canvas ID to Name and SIS ID."""
    workdir = Path(workdir)
    conversion = {}
    with open(workdir / "conversion.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for i, row in enumerate(reader):
            if i == 0:
                continue
            else:
                conversion[row[0]] = row[1:]
    return conversion


def get_sis_id_to_canvas_id_table(*, workdir: Union[Path, str] = "."):
    workdir = Path(workdir)
    sis_id_to_canvas = {}
    with open(workdir / "classlist.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for i, row in enumerate(reader):
            if i == 0:
                continue
            else:
                sis_id_to_canvas[row[-1]] = row[1]
    return sis_id_to_canvas


def get_courses_teaching(user):
    """Get a list of the courses a particular user is teaching.

    Args:
        user (canvasapi.current_user.CurrentUser)

    Returns:
        list: List of `canvasapi.course.Course` objects.
    """
    courses_teaching = []
    for course in user.get_courses():
        try:
            for enrollee in course.enrollments:
                if enrollee["user_id"] == user.id:
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


def interactively_get_course(user):
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
    print("\n")
    return course


def interactively_get_section(course, can_choose_none=True):
    """Choose a section (or not choice) from a menu.

    Returns:
        None/canvasapi.section.Section: None or a section object.
    """
    print(f"\nSelect a Section from {course}.\n")
    print("  Available Sections:")
    print("  --------------------------------------------------------------------")

    if not can_choose_none:
        raise NotImplementedError("Sorry, not implemented yet")

    sections = list(course.get_sections())
    i = 0
    if can_choose_none:
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
                return section


def interactively_get_assignment(course):
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
    print("\n")
    return assignment


def get_course_by_partial_name(course_name, user):
    # TODO: currently unused I think
    # TODO: better to warn if multiple matches instead of first one?
    for course in get_courses_teaching(user):
        if course_name in course.name:
            return course
    raise ValueError("Could not find a matching course")


def get_course_by_id_number(course_number, user):
    for course in get_courses_teaching(user):
        if course_number == course.id:
            return course
    raise ValueError("Could not find a matching course")


def get_assignment_by_id_number(course, num):
    for assignment in course.get_assignments():
        if assignment.id == num:
            return assignment
    raise ValueError(f"Could not find assignment matching id={num}")


def get_section_by_id_number(course, num):
    for section in course.get_sections():
        if section.id == num:
            return section
    raise ValueError(f"Could not find section matching id={num}")


def canvas_login(
    api_url: str | None = None, api_key: str | None = None
) -> Canvas.current_user.CurrentUser:
    """Login to a Canvas server using an API key.

    Args:
        api_url: server to login to, uses a default if omitted.
        api_key: the API key.  Will load from disc if
            omitted (deprecated!).

    Returns:
        The user who canvasapi.current_user.CurrentUser
    """
    if not api_url:
        api_url = __DEFAULT_CANVAS_API_URL__
    if not api_key:
        warn(
            "Loading from `api_secrets.py` is deprecated: consider changing your script to use env vars instead",
            category=DeprecationWarning,
        )
        from api_secrets import my_key as API_KEY  # pyright: ignore

        api_key = API_KEY
        del API_KEY
    canvas = Canvas(api_url, api_key)
    this_user = canvas.get_current_user()
    del canvas
    return this_user
