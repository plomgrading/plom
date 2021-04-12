#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi

"""Scripts that do the actual interfacing with Canvas api
"""

import canvasapi as capi
import canvasapi_extensions as cext

import os
import subprocess


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

    # We wrap it in User() to get the extended functionality given in
    # canvasapi_extensions
    user = cext.User(_canvas.get_current_user())

    del API_KEY, _canvas  # This probably doesn't do anything
    return user


def local_login(API_URL="https://canvas.ubc.ca"):
    # Expects `my_key` to be a string containing the api key assigned
    # to the user by Canvas
    from api_secrets import my_key as API_KEY

    user = login(API_URL, API_KEY)

    del API_KEY, API_URL
    return user


def select_from_list(
    options,
    things_choosing="choice",
    indentation=2,
    request_confirmation=True,
    sep_char="-",
    max_display_cols=70,
):
    """
    A really simple command line interface for choosing inputs
    interactively.

    args:
        options: The list of options we can pick from.

    kwargs:
        things_choosing: A string describing "what" we're trying to
                         choose currently (e.g. courses, assignments,
                         ...)

        indentation: How many whitespace characters to left-pad the
                     options with.

        request_confirmation: Bool determining whether or not we ask
                              y/n to confirm each choice. Defaults to
                              True

        sep_char: The character to use use in making the horizontal
                  separation bar that distinguishes the prompt
                  ("Select a <things_choosing>.") from the options
                  ("[<n>]: <thing>")

        max_display_cols: The rightmost limit for the separation bar
    """

    ### First, we construct the text menu for the user in three parts.
    header = f"Select a {things_choosing}."

    separator = f"{indentation*' '}{(max_display_cols-indentation)*sep_char}"

    # Separate entries with newlines and indent by `indentation` many
    # space characters
    candidate_list = "\n".join(
        [f"{indentation*' '}{i}: {option}" for (i, option) in enumerate(options)]
    )

    # Print the combined menu thingy.
    print(f"{header}\n{separator}\n{candidate_list}")

    # Thing that separates this list from later inputs
    footer = f"\n{max_display_cols*'='}\n\n"

    ### Enter loop until we can verify that the user presented a valid
    ### input & that .
    max_n = len(options) - 1
    if max_n < 0:
        print("Course has no assignments to mark.")
        return

    while True:
        choice = input(f"\n{indentation*' '}Choice [0-{max_n}]: ")
        try:
            # These two lines can trip the exceptions below (this
            # serves as lowkey input verification. We're just vibing
            # here y'all)
            choice = int(choice)
            assert choice >= 0 and choice <= max_n

            # Input `verified` by this point
            print(separator)

            selection = options[choice]

            if request_confirmation:
                print(f"{indentation*' '}You selected {choice}: {selection}")
                confirmation = input(f"{indentation*' '}Confirm selection? [y/n] ")
                if confirmation not in ["y", "Y"]:
                    continue  # Repeat the loop if invalid confirmation

            # Vertically separate from whatever's next
            print(footer)

            return selection

        except ValueError:
            print("Please respond with a nonnegative integer.")

        except AssertionError:
            if choice < 0:
                print("Choice must be nonnegative.")
            else:
                print(f"Choice to large (max is {max_n}).")

        # This should never happen
        except IndexError:
            print(
                "Alight Forest you must have messed up with an off-by-one error or something. tsk tsk you would REALLY think that after all these years maybe (just maybe) you wouldn't get so confused about Python and indexing and all this other stuff but noOooOoOo you just HAD to push to production without testing anything didn't you??? For shame! Seriously, for shame."
            )


def interactive_course_selection(user):
    """
    Interactively determine which course to mark and what directory to
    place the plom information in.

    args:
        user: an instance of `cext.User()`.
    """

    # Fetch the list of courses we're teaching and have the user
    # select one
    courses_teaching = [cext.Course(_) for _ in user.get_courses_teaching()]
    course = select_from_list(courses_teaching, things_choosing="course")

    # Fetch the list of assignments for this course and have the user
    # select one.
    #
    # TODO: Filter to only show assignments that have submissions that
    # need to be graded
    #
    # TODO: Figure out whether we want to extend the Assignment class
    # at all and replace the line below [which essentially does
    # list(<canvasapi_paginated_list>) so that we can actually figure
    # out the max length] with something containing
    # `cext.Assignment(_)`.
    assignments = [_ for _ in course.get_assignments() if _.needs_grading_count > 0]
    assignment = select_from_list(assignments, things_choosing="assignment")

    # This can happen if the course has no assignments.
    if assignment is None:
        return

    return (course, assignment)


def mcd_server_dirs():
    """
    mcd --> `m` from `mk`, `c` from `ch`, `d` for `dir`. Basically,
    generate the plom server directories if they don't exist;
    otherwise cd into them.

    Assumes that the current directory is where all of the plom server
    files and such should be deposited. So be sure to put the call to
    `()` inside of some `chdir()` calls if you want files deposited elsewhere.


    TODO: Might be nice to store a local information file (e.g. in
          `~/.local/share/plom`) that keeps track of
          previously-created plom server directories so the user
          doesn't have to manually go through this dialogue each
          time...maybe we could start defaulting to placing the
          server directories there as well? Although we'd probably
          want to be sure we remove all sensitive student info at the
          end of each session...? hmm
    """
    _excluded_dirs = ["__pycache__"]  # TODO: Others?

    classdirs = [
        _ for _ in os.listdir() if os.path.isdir(_) and _ not in _excluded_dirs
    ]
    classdir = select_from_list(classdirs, things_choosing="subdir for the class")

    # UNFINISHED


if __name__ == "__main__":
    user = local_login()
    (course, assignment) = interactive_course_selection(user)

    # # TODO: Make this give an `os.listdir()`
    # print("Setting up the workspace now.\n")
    # print("  Current subdirectories:")
    # print("  --------------------------------------------------------------------")
    # excluded_dirs = ["__pycache__"]
    # subdirs = [
    #     subdir
    #     for subdir in os.listdir()
    #     if os.path.isdir(subdir) and subdir not in excluded_dirs
    # ]
    # for subdir in subdirs:
    #     print(f"    ./{subdir}")

    # classdir_selected = False
    # while not classdir_selected:

    #     classdir_name = input(
    #         "\n  Name of dir to use for this class (will create if not found): "
    #     )

    #     if not classdir_name:
    #         print("    Please provide a non-empty name.\n")
    #         continue

    #     print(f"  You selected `{classdir_name}`")
    #     confirmation = input("  Confirm choice? [y/n] ")
    #     if confirmation in ["", "\n", "y", "Y"]:
    #         classdir_selected = True
    #         classdir = classdir_name

    # print(f"\n  cding into {classdir}...")
    # if os.path.exists(classdir_name):
    #     os.chdir(classdir)
    # else:
    #     os.mkdir(classdir)
    #     os.chdir(classdir)

    # print(f"  working directory is now `{os.getcwd()}`")

    # print("\n\n\n")

    # print("  Current subdirectories:")
    # print("  --------------------------------------------------------------------")
    # subdirs = [
    #     subdir
    #     for subdir in os.listdir()
    #     if os.path.isdir(subdir) and subdir not in excluded_dirs
    # ]
    # # subdirs = [_ for _ in os.listdir if os.path.isdir(_)]
    # for subdir in subdirs:
    #     print(f"    ./{subdir}")

    # # Directory for this particular assignment
    # hwdir_selected = False
    # while not hwdir_selected:

    #     hwdir_name = input(
    #         "\n\n\n  Name of dir to use for this assignment (will create if not found): "
    #     )

    #     print(f"  You selected `{hwdir_name}`")
    #     confirmation = input("  Confirm choice? [y/n] ")
    #     if confirmation in ["", "\n", "y", "Y"]:
    #         hwdir_selected = True
    #         hwdir = hwdir_name

    # print(f"\n  cding into {hwdir}...")
    # if os.path.exists(hwdir_name):
    #     os.chdir(hwdir)
    # else:
    #     os.mkdir(hwdir)
    #     os.chdir(hwdir)

    # print(f"  working directory is now `{os.getcwd()}`")

    # plom_server = initialize(course, assignment)

    # print("\n\ngetting submissions from canvas...")
    # get_submissions(assignment, dry_run=False)

    # print("scanning submissions...")
    # scan_submissions()

    # # Return to starting directory
    # os.chdir(o_dir)
