from canvasapi import Canvas

import os
import csv
import subprocess
import string
from tqdm import tqdm as tqdm

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
    sid_to_canvas = {}
    with open(f"{server_dir}/classlist.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                sid_to_canvas[row[-1]] = row[1]
    return sid_to_canvas


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


def get_sid_to_sub_table(subs):
    # Why the heck is canvas so stupid about not associating student
    # IDs with student submissions
    conversion = get_conversion_table()

    sid_to_sub = {}
    for sub in subs:
        canvas_id = sub.user_id
        _, sis_id = conversion[str(canvas_id)]
        sid_to_sub[sis_id] = sub

    return sid_to_sub


def get_sid_to_marks():
    sid_to_marks = {}
    with open("marks.csv", "r") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')

        for (i, row) in enumerate(reader):
            if i == 0:
                continue
            else:
                # print(row[0], row[-3])
                sid_to_marks[row[0]] = row[-3]
    return sid_to_marks


if __name__ == "__main__":
    # TODO: Fix all the `sis` vs `sid` garbage here
    user = login()

    o_dir = os.getcwd()

    courses = get_courses_teaching(user)
    for course in courses:
        # Hard-coded: Course name to push. TODO: replace with TUI
        if "340 202" in course.name:
            m340 = course

    student_list = get_student_list(m340)
    sis_id_to_students = sis_id_to_student_dict(student_list)

    for assignment in m340.get_assignments():
        # if assignment.name == "Homework 2 Problem 1":
        #     assgn = assignment
        if "Homework 2 Problem 1" in assignment.name:
            assgn = assignment

    subs = assgn.get_submissions()

    os.chdir("m340/hw2-p1")
    sid_to_sub = get_sid_to_sub_table(subs)
    # We only need this second one for double-checking everything is
    # in order
    sid_to_canvas = get_sis_id_to_canvas_id_table(server_dir=".")

    sid_to_marks = get_sid_to_marks()
    os.chdir("reassembled")

    # TODO: Give this a nice TUI

    pdfs = [fname for fname in os.listdir() if fname[-4:] == ".pdf"]
    bad = []
    for pdf in tqdm(pdfs):
        sis_id = (pdf.split("_")[1]).split(".")[0]
        assert len(sis_id) == 8
        assert set(sis_id) <= set(string.digits)
        sub = sid_to_sub[sis_id]
        student = sis_id_to_students[sis_id]
        mark = sid_to_marks[sis_id]
        assert sub.user_id == student.user_id
        # try:
        #     if sub.submission_comments:
        #         print(sub.submission_comments)
        #     else:
        #         print("mising")
        # except AttributeError:
        #     print("no")
        #     pass
        try:
            sub.upload_comment(pdf)
        except:  # Can get a `CanvasException` here from timeouts
            bad += [pdf]
        sub.edit(submission={"posted_grade": mark})

    # Ones we'll have to upload manually
    print(bad)

    os.chdir(o_dir)
