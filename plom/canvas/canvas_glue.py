#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi

"""Get information from all the canvas courses and such
"""

from copy import deepcopy

import canvasapi as capi

# Extend the CurrentUser class to add some helpful methods, e.g. one
# to only fetch course
class User(capi.current_user.CurrentUser):
    def __init__(self, capi_user):

        # Ensure that we got the right thing passed in
        assert isinstance(capi_user, capi.current_user.CurrentUser)

        # Keep a copy of the underlying user object
        self.underlying = capi_user

        return

    def __getattr__(self, attr):
        """
        Silently pull attributes from the `capi_user` object we're
        extending here.
        """
        return getattr(self.underlying, attr)

    def get_courses_teaching(self):
        """
        Get a list of courses in which the user has instructor status
        """
        teaching = []
        for course in list(self.get_courses()):
            try:
                for enrollee in course.enrollments:  # Necessary?
                    if (enrollee["user_id"] == self.id) and (
                        enrollee["type"] in ["teacher", "ta"]
                    ):
                        teaching += [course]
            except AttributeError:
                # It looks like old courses that are no longer active
                # still show up here, but because we've lost access to
                # them, we can't query any attributes. The assertion
                # here basically just ensure that that's actually
                # what's going on.
                #
                # TODO: INvestigate further?
                try:
                    assert course.access_restricted_by_date
                except AttributeError:
                    print(f"Course {course} has no such attribute.")
                    # print(dir(course))
        self.teaching = teaching
        return teaching


# Extend the course.Course class to add some helpful methods, e.g. one
# to fetch all students in the course
class Course(capi.course.Course):
    def __init__(self, capi_course):

        # Ensure that we got the right thing passed in
        assert isinstance(capi_course, capi.course.Course)

        # Keep a copy of the original course
        self.underlying = capi_course

        self.populate_class_info()
        return

    def __getattr__(self, attr):
        """
        Silently pull attributes from the `capi_course` object we're
        extending here.
        """
        return getattr(self.underlying, attr)

    def __repr__(self):
        str_rep = f"Course(name={self.course_code})"
        return str_rep

    def get_students(self):
        """
        Get a list of the students in the class
        """
        students = [_ for _ in self.get_enrollments() if _.role == "StudentEnrollment"]
        self.students = students
        return students

    def populate_class_info(self):
        """
        Plom needs a csv with the classlist data
        """

        try:
            students = self.students
        except AttributeError:
            students = self.get_students()

        classlist = [
            (
                "Student",
                "ID",
                "SIS User ID",
                "SIS Login ID",
                "Section",
                "Student Number",
            )
        ]

        by_name = {}
        by_stud_id = {}
        by_sis_id = {}

        for stud in students:
            try:
                stud_name, stud_id, stud_sis_id, stud_sis_login_id = (
                    stud.user["sortable_name"],
                    stud.id,
                    stud.sis_user_id,
                    stud.user["integration_id"],
                )

                # Add this information to the table we'll write out to
                # the CSV
                classlist += [
                    (
                        stud_name,
                        stud_id,
                        stud_sis_id,
                        stud_sis_login_id,
                        self.name,
                        stud_sis_id,
                    )
                ]

                by_name[stud_name] = stud
                by_stud_id[stud_id] = stud
                by_sis_id[stud_sis_id] = stud

            except AttributeError:
                assert stud.user["name"] == "Test Student"

        self._classlist_csv = classlist
        self._by_name = by_name
        self._by_stud_id = by_stud_id
        self._by_sis_id = by_sis_id

        return


def login(API_URL, API_KEY):
    """
    Instantiate a canvasapi object for the user by logging into
    API_URL with API_KEY.

    Example call:
        login(
            "https://canvas.ubc.ca",
            "12345~uJcFOtJm0uOzZeAERsBLAhCOCU7zg5etm45yVGHLJ9FlgTiteuGmxFTwpBNcC4qd"
        )
    """
    _canvas = capi.Canvas(API_URL, API_KEY)
    user = _canvas.get_current_user()
    del API_KEY, _canvas  # This probably doesn't do anything
    return user


def test_login():
    from api_secrets import my_key as API_KEY

    API_URL = "https://canvas.ubc.ca"
    user = login(API_URL, API_KEY)
    user = User(user)
    del API_KEY, API_URL
    return user


if __name__ == "__main__":
    user = test_login()
    user.get_courses_teaching()
    m340 = user.teaching[-3]
    m340C = Course(m340)
