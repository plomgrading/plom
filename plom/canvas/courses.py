#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2020 Forest Kobayashi

"""Get information from all the canvas courses and such
"""

# TODO: figure out why the permissions on my API key changed (making
# this command no longer work )
# from canvas_login import user as user
from .canvas_login import canvas as canvas
from .canvas_login import user as user

import csv
import string
import subprocess
import os


def get_relevant_courses():
    """
    Return a dictionary with
        keys: names of the courses in which the user has teacher/ta
              privileges
        values: `canvasapi` objects representing said courses
    """

    # Returns a lazy-evaluated list of courses. We'll iterate through
    # it below to filter out ones in which our account doesn't have
    # instructor privileges.
    canvas_courses = canvas.get_courses()

    # Initialize
    courses_teaching = []
    for course in canvas_courses:

        try:
            enrollees = course.enrollments

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
            print(f"WARNING: At least one course is missing some expected attributes")

    # The default format for courses in the canvas API is not very
    # human readable. We'll create a list of names, and then associate
    # those to the canvas course objects using the following dict.
    relevant_courses_dict = {course.name: course for course in courses_teaching}
    return relevant_courses_dict


def get_classlist(course, server_dir="."):
    """
    (course): A canvasapi course object

    Get a csv spreadsheet with entries of the form (student ID,
    student name)
    """
    enrollments_raw = course.get_enrollments()
    students = [_ for _ in enrollments_raw if _.role == "StudentEnrollment"]

    # Missing information doesn't reaaaaaaaaally matter to us so we'll
    # just fill it in as needed
    default_id = 0  # ? not sure how many digits this can be. I've seen 5-7
    default_sis_id = 0  # 8-digit number
    default_sis_login_id = 0  # 12-char jumble of letters and digits

    classlist = [
        ("Student", "ID", "SIS User ID", "SIS Login ID", "Section", "Student Number")
    ]

    for stud in students:

        stud_name, stud_id, stud_sis_id, stud_sis_login_id = (
            stud.user["sortable_name"],
            stud.id,
            stud.sis_user_id,
            stud.user["integration_id"],
        )

        for (this_id, this_default, num_digits) in [
            (stud_id, default_id, 7),
            (stud_sis_id, default_sis_id, 8),
            (stud_sis_login_id, default_sis_login_id, 12),
        ]:

            if not this_id:
                # Too lazy to figure out how to pad with nested
                # fstrings
                this_id = str(this_default)
                this_id = (num_digits - len(this_id)) * "0" + this_id
                this_default += 1

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

    with open(f"{server_dir}/classlist.csv", "w", newline="\n") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(classlist)

    return


def filter_for_qr(info_str):
    """
    args:

    (info_str): a string representing a field for one of the entries
    in a Spec.toml file

    returns:

    (filtered_str): a string with any illegal characters that could
    mess up a QR code removed
    """
    # lower case letters, upper case letters, digits, and the space
    # character
    allowed_chars = set(string.ascii_letters + string.digits + " ")
    filtered_str = ""
    for char in info_str:
        if char in allowed_chars:
            filtered_str += char
    return filtered_str


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
    longName = filter_for_qr(assignment.name)

    name = get_short_name(longName)

    numberOfVersions = 1  # TODO: Make this not hardcoded
    numberOfPages = 20  # TODO: Make this not hardcoded
    numberToProduce = len([_ for _ in assignment.get_gradeable_students()])
    numberToName = assignment.needs_grading_count

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
    toml += f"mark={assignment.points_possible if assignment.points_possible else 1}\n"
    toml += 'select="fix"'

    with open(f"{server_dir}/canvasSpec.toml", "w") as f:
        f.write(toml)


def initialize(server_dir="../../server-test"):
    o_dir = os.getcwd()  # original directory

    # Try except is just here while testing
    try:
        get_classlist(sbox, server_dir=server_dir)
        get_toml(assignment, server_dir=server_dir)

        os.chdir(server_dir)
        subprocess.run(["plom-build", "parse", "canvasSpec.toml"])

        subprocess.run(["plom-server", "init"])

        subprocess.run(["plom-server", "users", "--auto", "1"])

        totally_insecure_nonsense = []
        with open("serverConfiguration/userListRaw.csv", "r") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                totally_insecure_nonsense += [row]

        subprocess.run(["plom-server", "users", "serverConfiguration/userListRaw.csv"])

        # launch the server as a background process
        plom_server = subprocess.Popen(["plom-server", "launch"])

        build_class = subprocess.Popen(["plom-build", "class", "classlist.csv"])
        # Pass the manager password into the prompt
        build_class.stdin.write(totally_insecure_nonsense[1][1] + "\n")
        build_class.stdin.flush()

    except:
        pass

    os.chdir(o_dir)

    return plom_server


def get_submissions(assignment):
    pass
