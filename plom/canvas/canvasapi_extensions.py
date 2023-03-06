# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2023 Colin B. Macdonald

"""Get information from all the canvas courses and such

TODO: Currently unused, deprecated or WIP?
"""

from pathlib import Path

import canvasapi as capi


# FIRST UP: Extending the canvas api classes to add some nice
# methods for integration with plom.


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

        It might be better form to make a call to `super(...)` but
        supplying the correct arguments seems like it'd be a bit
        Kafkaesque so that's a no go from me...
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

        return

    def __getattr__(self, attr):
        """
        Silently pull attributes from the `capi_course` object we're
        extending here.
        """
        return getattr(self.underlying, attr)

    def __str__(self):
        """
        The inherited `__str__()` includes a lot of irrelevant
        information so we overwrite here to just show course code.
        """
        # TODO: Figure out whether we really want `course_code` as
        # opposed to `name`
        return self.course_code

    def get_students(self):
        """
        Get a list of the students in the class

        TODO: careful, does not consider which Section so possible to get duplicates.
        """
        students = [_ for _ in self.get_enrollments() if _.role == "StudentEnrollment"]
        self.students = students
        return students

    def populate_class_info(self):
        """
        Get
            (1) the csv that plom wants to refer to for course info
            (2) conversion tables associating the various ID tags to
                canvas uses to the corresponding `Student` objects,
                and
            (3) store these as attributes of the extended Course
                object!
        """

        try:
            students = self.students
        except AttributeError:
            students = self.get_students()

        # Head row of classlist csv
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

        # Instantiate conversion tables
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

        self.classlist_csv = classlist

        # Conversion tables
        self.by_name = by_name
        self.by_stud_id = by_stud_id
        self.by_sis_id = by_sis_id

        return

    def write_classlist_csv(self, plom_server_path):
        """
        path should be the path of the plom server directory.
        """
        fname = Path(plom_server_path) / "classlist.csv"
        with open(fname, "w") as f:
            f.write(self.classlist_csv)
