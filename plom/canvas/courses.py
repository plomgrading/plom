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
