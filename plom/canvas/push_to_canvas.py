from canvasapi import Canvas

import os
import csv
import subprocess
import string
import time
import random

import pandas
from tqdm import tqdm as tqdm

# TODO: or how else to get the classlist and conversion?
from canvas_server import get_classlist as make_conversion_csv


# TODO: Refactor this into a separate canvas methods file
def get_conversion_table(server_dir="."):
    """
    convert canvas ID to name and sis id
    """
    conversion = {}
    with open(f"{server_dir}/conversion.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                conversion[row[0]] = row[1:]
    return conversion


def get_sis_id_to_canvas_id_table(server_dir="."):
    sis_id_to_canvas = {}
    with open(f"{server_dir}/classlist.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                sis_id_to_canvas[row[-1]] = row[1]
    return sis_id_to_canvas


def get_courses_teaching(user):
    courses_teaching = []
    for course in user.get_courses():

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
            # print(f"WARNING: At least one course is missing some expected attributes")
            pass

    return courses_teaching


def get_course(course_name, user):
    for course in get_courses_teaching(user):
        if course_name in course.name:
            return course


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
            assert not student.sis_user_id is None
        except AssertionError:
            # print(student.user_id)
            pass
            # print(student.)
        out_dict[student.sis_user_id] = student
    return out_dict


def login():
    from api_secrets import my_key as API_KEY

    API_URL = "https://canvas.ubc.ca"

    canvas = Canvas(API_URL, API_KEY)
    del API_KEY
    this_user = canvas.get_current_user()
    del canvas
    return this_user


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


def obfuscate_student_name(stud_name):
    output = ""
    pieces = stud_name.split(", ")
    for substr in pieces:
        head = substr[:2]
        tail = substr[2:]
        for char in string.ascii_letters + string.punctuation:
            tail = tail.replace(char, "*")
        output += head + tail + ", "
    return output[:-2]  # remove final comma


def obfuscate_reassembled_pdfname(pdfname):
    prefix, postfix = pdfname.split("_")
    sis_id, _ = postfix.split(".")  # We don't care about the "pdf"
    sis_id = sis_id[0] + (len(sis_id) - 2) * "*" + sis_id[-1]
    return f"{prefix}_{sis_id}.pdf"


if __name__ == "__main__":
    # TODO: Fix all the `sis` vs `sis_id` garbage here
    user = login()

    o_dir = os.getcwd()

    # To avoid having to input things like a billion times
    # mgr_pass = input("plom manager password: ")
    # os.environ["PLOM_MANAGER_PASSWORD"] = mgr_pass
    # del mgr_pass

    courses_teaching = get_courses_teaching(user)

    print("\nSelect a course to push grades for.\n")
    print("  Available courses:")
    print("  --------------------------------------------------------------------")
    for (i, course) in enumerate(courses_teaching):
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

    # print("\n  ==================================================================  ")
    print("\n\n")

    print(f"\nSelect an assignment to push for {course}.\n")
    print("  Available assignments:")
    print("  --------------------------------------------------------------------")

    assignments = list(course.get_assignments())
    for (i, assignment) in enumerate(assignments):
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

    print(
        "\n======================================================================\n\n\n\n"
    )

    # TODO: Make this give an `os.listdir()`
    print("Which current subdirectory corresponds to the class?\n")
    print("  Current subdirectories:")
    print("  --------------------------------------------------------------------")
    excluded_dirs = ["__pycache__"]
    subdirs = [
        subdir
        for subdir in os.listdir()
        if os.path.isdir(subdir) and subdir not in excluded_dirs
    ]
    for (i, subdir) in enumerate(subdirs):
        print(f"    {i}: {subdir}")

    subdir_chosen = False
    while not subdir_chosen:
        choice = input("\n  Choice [0-n]: ")

        if not (set(choice) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(choice) >= len(subdirs):
            print("Choice too large.")
        else:
            choice = int(choice)
            print(
                "  --------------------------------------------------------------------"
            )

            selection = subdirs[choice]
            print(f"  You selected {choice}: {selection}")
            confirmation = input("  Confirm choice? [y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                subdir_chosen = True
                subdir = selection
                break

    os.chdir(selection)
    print(f"  working directory is now `{os.getcwd()}`")

    print("\n\n\n")
    print("Which current subdirectory corresponds to the assignment?\n")
    print("  Current subdirectories:")
    print("  --------------------------------------------------------------------")

    subdirs = [
        subdir
        for subdir in os.listdir()
        if os.path.isdir(subdir) and subdir not in excluded_dirs
    ]
    for (i, subdir) in enumerate(subdirs):
        print(f"    {i}: {subdir}")

    subdir_chosen = False
    while not subdir_chosen:
        choice = input("\n  Choice [0-n]: ")

        if not (set(choice) <= set(string.digits)):
            print("Please respond with a nonnegative integer.")
        elif int(choice) >= len(subdirs):
            print("Choice too large.")
        else:
            choice = int(choice)
            print(
                "  --------------------------------------------------------------------"
            )

            selection = subdirs[choice]
            print(f"  You selected {choice}: {selection}")
            confirmation = input("  Confirm choice? [y/n] ")
            if confirmation in ["", "\n", "y", "Y"]:
                subdir_chosen = True
                subdir = selection
                break

    os.chdir(selection)

    print(f"  working directory is now `{os.getcwd()}`")

    print("\n\n\nRunning `plom-finish`...")
    print("  --------------------------------------------------------------------")
    print("  Building csv of marks...")
    # TODO: Use return value from subprocess to determine whether we
    # first need to run plom-finish clear
    subprocess.run(["plom-finish", "csv"])
    print("\n  Reassembling pdfs...")
    subprocess.run(["plom-finish", "reassemble"])
    print("\n  Finished `plom-finish`.")

    print("\n\n\nFetching data from canvas now...")
    print("  --------------------------------------------------------------------")
    print("  Getting student list...")
    student_list = get_student_list(course)
    print("  Done.\n")
    print("  Getting canvasapi submission objects...")
    subs = assignment.get_submissions()
    print("  Done.\n")

    # Most of these conversion tables are fully irrelevant once we
    # test this code enough to be confident we can remove the
    # assertions down below
    print("  Constructing SIS_ID to student conversion table...")
    sis_id_to_students = sis_id_to_student_dict(student_list)
    print("  Done.\n")

    print("  Constructing SIS_ID to canvasapi submission conversion table...")
    sis_id_to_sub_and_name = get_sis_id_to_sub_and_name_table(subs)
    print("  Done.\n")

    print("  Constructing SIS_ID to canvasapi submission conversion table...")
    # We only need this second one for double-checking everything is
    # in order
    sis_id_to_canvas = get_sis_id_to_canvas_id_table(server_dir=".")
    print("  Done.\n")

    print("  Finally, getting SIS_ID to marks conversion table.")
    sis_id_to_marks = get_sis_id_to_marks()
    print("  Done.\n")

    print("\n\n\nPushing grades to Canvas...")
    print("  --------------------------------------------------------------------")
    os.chdir("reassembled")
    pdfs = [fname for fname in os.listdir() if fname[-4:] == ".pdf"]

    dry_run = False
    timeouts = []
    for pdf in tqdm(pdfs):
        sis_id = (pdf.split("_")[1]).split(".")[0]
        assert len(sis_id) == 8
        assert set(sis_id) <= set(string.digits)
        sub, name = sis_id_to_sub_and_name[sis_id]
        student = sis_id_to_students[sis_id]
        mark = sis_id_to_marks[sis_id]
        assert sub.user_id == student.user_id
        # try:
        #     if sub.submission_comments:
        #         print(sub.submission_comments)
        #     else:
        #         print("mising")
        # except AttributeError:
        #     print("no")
        #     pass
        if dry_run:
            timeouts += [(pdf, name)]
        else:
            try:
                sub.upload_comment(pdf)
                time.sleep(random.uniform(2, 6))
            except:  # Can get a `CanvasException` here from timeouts
                timeouts += [(pdf, name)]

            # Push the grade change
            sub.edit(submission={"posted_grade": mark})

    # Ones we'll have to upload manually
    print(f"  Done. There were {len(timeouts)} timeouts.")

    continue_after = True
    while not True:
        view_timeouts = input("  View them? [y/n]")
        if view_timeouts in ["", "\n", "y", "Y"]:
            break
        elif view_timeouts in ["n", "N"]:
            continue_after = False
        else:
            print("  Please select one of [y/n].")

    while continue_after:
        obfuscate = input("  Obfuscate student info? [y/n] ")
        if obfuscate in ["n", "N"]:
            print(f"         filename      (student name)")
            print("    --------------------------------")
            print(
                "    ------------------------------------------------------------------"
            )
            for (i, timed_out) in enumerate(timeouts):

                print(f"    {timed_out[0]}  ({timed_out[1]})")
            print("  These should be uploaded manually.\n")
            break
        elif obfuscate in ["", "\n", "y", "Y"]:
            print(f"        filename      (student name)")
            for (i, timed_out) in enumerate(timeouts):

                print(
                    f"    {obfuscate_reassembled_pdfname(timed_out[0])}  ({obfuscate_student_name(timed_out[1])})"
                )
            print("  These should be uploaded manually.\n")
            break
        else:
            print("  Please select one of [y/n].")

    print("Have a nice day!")
    os.chdir(o_dir)
