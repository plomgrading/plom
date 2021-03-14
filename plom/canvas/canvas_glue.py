#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi

"""Get information from all the canvas courses and such
"""

import canvasapi as capi

# Extend the CurrentUser class to add some helpful methods, e.g. one
# to only fetch course
class User(capi.current_user.CurrentUser):
    def __init__(self, capi_user):

        # Ensure that we got the right thing passed in
        assert isinstance(capi_user, capi.current_user.CurrentUser)

        # capi_user.__init__(self)

        self.canvas = capi_user
        return

    def get_courses(self):
        return self.canvas.get_courses()

    def get_courses_teaching(self):
        """
        Get a list of courses in which the user has instructor status
        """
        teaching = []
        for course in self.get_courses():
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
                    print(dir(course))
        self.teaching = teaching
        return teaching


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
