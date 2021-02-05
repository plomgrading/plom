#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi

"""Get information from all the canvas courses and such
"""

import csv
import string
import subprocess
import os
from tqdm import tqdm as tqdm


def get_classlist(course, server_dir="."):
    """
    (course): A canvasapi course object

    Get a csv spreadsheet with entries of the form (student ID,
    student name)
    """
    enrollments_raw = course.get_enrollments()
    students = [_ for _ in enrollments_raw if _.role == "StudentEnrollment"]

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
    numberToName = assignment.needs_grading_count  # This is bad form

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
    toml += f"mark={assignment.points_possible if assignment.points_possible else 1}\n"
    toml += 'select="fix"'

    with open(f"{server_dir}/canvasSpec.toml", "w") as f:
        f.write(toml)


def initialize(course, assignment, server_dir="server-test"):
    """
    Set up the test directory, get the classlist from canvas, make the
    .toml, etc
    """
    if not os.path.exists(server_dir):
        os.mkdir(server_dir)

    o_dir = os.getcwd()  # original directory

    print("Getting enrollment data from canvas and building `classlist.csv`...")
    get_classlist(course, server_dir=server_dir)

    print("Generating `canvasSpec.toml`...")
    get_toml(assignment, server_dir=server_dir)

    os.chdir(server_dir)
    print("\nSwitched into test server directory.\n")

    print("Parsing `canvasSpec.toml`...")
    subprocess.run(["plom-build", "parse", "canvasSpec.toml"], capture_output=True)

    print("Running `plom-server init`...")
    subprocess.run(["plom-server", "init"], capture_output=True)

    print("Autogenerating users...")
    subprocess.run(["plom-server", "users", "--auto", "1"], capture_output=True)

    print("Temporarily exporting manager passwo...")
    user_list = []
    with open("serverConfiguration/userListRaw.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            user_list += [row]

    os.environ["PLOM_MANAGER_PASSWORD"] = user_list[1][1][2:-1]

    del user_list

    print("Processing userlist...")
    subprocess.run(
        ["plom-server", "users", "serverConfiguration/userListRaw.csv"],
        capture_output=True,
    )

    # We formerly launched the server permanently, but it was mucking
    # up the pretty `tqdm` bars, so I removed that for now. The
    # associated print statements were
    #
    #    print("\nRelaunching the server in the __main__ scope...")
    #
    # and
    #
    # print(
    #     "Server *should* be running now (although we can't really tell since we've supressed the output). In light of this, be extra sure to explicitly kill the server (e.g., `pkill plom-server`) before trying to start a new one --- it can persist even after the original python process has been killed.\n\nTo verify if the server is running, you can try the command\n  ss -lntu\nto check if the 41984 port has a listener.\n"
    # )

    print("Launching the server temporarily...")
    # launch the server as a background process. To suppress output,
    # we're going to pipe it into /dev/null.

    plom_server = subprocess.Popen(["plom-server", "launch"], stdout=subprocess.DEVNULL)

    subprocess.run(["sleep", "3"])

    print("Building classlist...")
    build_class = subprocess.run(
        ["plom-build", "class", "classlist.csv"], capture_output=True
    )

    os.chdir(o_dir)

    print("killing the server.")
    plom_server.kill()
    return  # plom_server


def get_submissions(assignment, server_dir="server-test"):
    """
    get the submission pdfs out of Canvas
    """
    o_dir = os.getcwd()

    os.chdir(server_dir)

    if not os.path.exists("upload"):
        os.mkdir("upload")

    os.chdir("upload")

    print("Moved into server-test/upload")

    print("Fetching submissions...")
    subs = list(assignment.get_submissions())

    # TODO: Parallelize requests
    unsubmitted = []
    for sub in tqdm(subs):  # TODO: is `aria2c` actually faster here lol??
        sub_name = f"{sub.user_id}.pdf"
        if not (sub.url is None):
            sub_url = sub.url
            subprocess.run(["aria2c", sub_url, "-o", sub_name], capture_output=True)
        else:
            try:
                for obj in sub.attachments:
                    if type(obj) == dict:
                        sub_url = obj["url"]
                subprocess.run(["aria2c", sub_url, "-o", sub_name], capture_output=True)
            except AttributeError:  # Catches if student didn't submit
                unsubmitted += [sub]
                continue

    for sub in unsubmitted:
        print(f"No submission from user_id {sub.user_id}")

    os.chdir(o_dir)


def scan_submissions(server_dir="server-test"):
    """
    Apply `plom-scan` to all the pdfs we've just pulled from canvas
    """
    o_dir = os.getcwd()
    os.chdir(server_dir)

    user_list = []
    with open("serverConfiguration/userListRaw.csv", "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            user_list += [row]

    os.environ["PLOM_SCAN_PASSWORD"] = user_list[2][1][2:-1]

    os.chdir("upload")

    print("Temporarily exporting scanner password...")

    # TODO: Parallelize here
    print("Applying `plom-scan` to pdfs...")
    pdfs = [f for f in os.listdir() if ".pdf" == f[-4:]]
    for pdf in tqdm(pdfs):
        subprocess.run(["plom-scan", "process", pdf], capture_output=True)
        # TODO: Make sure the --unknown flag doesn't cause any
        # problems here
        subprocess.run(
            ["plom-scan", "upload", pdf[:-4], "--unknowns"], capture_output=True
        )

    os.chdir(o_dir)


def stupid_preamble():
    """
    This is the part where we open the connection to canvas
    """
    from canvasapi import Canvas

    from api_secrets import my_key as API_KEY

    API_URL = "https://canvas.ubc.ca"

    canvas = Canvas(API_URL, API_KEY)
    del API_KEY
    user = canvas.get_current_user()

    courses = list(user.get_courses())

    # Hard coded some courses of interest here for now
    for course in courses:
        try:
            if "Colin" in course.name:
                sbox = course
            if "340 202" in course.name:
                m340_202 = course
        except:
            pass

    assignments = list(m340_202.get_assignments())

    assignment = assignments[0]

    return m340_202, assignment


if __name__ == "__main__":

    course, assignment = stupid_preamble()

    initialize(course, assignment)

    print(
        "\n\nPlease start the plom server. Execution will continue assuming that you *have* in 10 seconds\n\n"
    )
    subprocess.run(["sleep", "10"])

    print("getting submissions from canvas...")
    get_submissions(assignment)
    scan_submissions()
