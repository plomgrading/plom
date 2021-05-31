# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021 Colin B. Macdonald

"""Misc utils for interacting with Canvas"""

import csv
from pathlib import Path
import string


def download_classlist(course, server_dir="."):
    """
    Download and .csv of the classlist and various conversion stables.

    Args:
        course: A canvasapi course object.
        server_dir (str/pathlib.Path): where to save the file.

    Returns:
        None

    TODO: spreadsheet with entries of the form (student ID, student name)
    TODO: so is it the plom classlist or something else?
    """
    server_dir = Path(server_dir)
    enrollments_raw = course.get_enrollments()
    students = [_ for _ in enrollments_raw if _.role == "StudentEnrollment"]

    # TODO: doc this in the docstring!
    # Missing information doesn't reaaaaaaaaally matter to us so we'll
    # just fill it in as needed.
    #
    # FIXME: This should probably contain checks to make sure we get
    # no collisions.
    default_id = 0  # ? not sure how many digits this can be. I've seen 5-7
    default_sis_id = 0  # 8-digit number
    default_sis_login_id = 0  # 12-char jumble of letters and digits

    classlist = [
        ("Student", "ID", "SIS User ID", "SIS Login ID", "Section", "Student Number")
    ]

    conversion = [("Internal Canvas ID", "Student", "SIS User ID")]

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
            or (type(stud_id) == str and stud_id in string.whitespace)
        ):
            stud_id = str(default_id)
            # 5-7 characters is what I've seen, so let's just go with 7
            stud_id = (7 - len(stud_id)) * "0" + stud_id
            default_id += 1

        if (
            not stud_sis_id
            or stud_sis_id is None
            or (type(stud_sis_id) == str and stud_sis_id in string.whitespace)
        ):
            stud_sis_id = str(default_sis_id)
            # 8 characters is necessary for UBC ID
            stud_sis_id = (8 - len(stud_sis_id)) * "0" + stud_sis_id
            default_sis_id += 1

        if (
            not stud_sis_login_id
            or stud_sis_login_id is None
            or (
                type(stud_sis_login_id) == str
                and stud_sis_login_id in string.whitespace
            )
        ):
            stud_sis_login_id = str(default_sis_login_id)
            stud_sis_login_id = (12 - len(stud_sis_login_id)) * "0" + stud_sis_login_id
            default_sis_login_id += 1

        # Add this information to the table we'll write out to the CSV
        classlist += [
            (
                stud_name,
                stud_id,
                stud_sis_id,
                stud_sis_login_id,
                course.name,
                stud_sis_id,
            )
        ]

        conversion += [(internal_canvas_id, stud_name, stud_sis_id)]

    with open(server_dir / "classlist.csv", "w", newline="\n") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(classlist)

    with open(server_dir / "conversion.csv", "w", newline="\n") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(conversion)


def get_conversion_table(server_dir="."):
    """A mapping Canvas ID to Name and SIS ID."""
    server_dir = Path(server_dir)
    conversion = {}
    with open(server_dir / "conversion.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                conversion[row[0]] = row[1:]
    return conversion


def get_sis_id_to_canvas_id_table(server_dir="."):
    server_dir = Path(server_dir)
    sis_id_to_canvas = {}
    with open(server_dir / "classlist.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                sis_id_to_canvas[row[-1]] = row[1]
    return sis_id_to_canvas


def get_courses_teaching(user):
    """Get a list of the courses a particular user is teaching.

    args:
        user (canvasapi.current_user.CurrentUser)

    return:
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
