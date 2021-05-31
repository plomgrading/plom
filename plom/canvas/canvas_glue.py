#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi

"""Scripts that do the actual interfacing with Canvas api
"""

import csv
import os
import subprocess

import canvasapi as capi
import canvasapi_extensions as cext


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


# TODO: put an `allow other` choice in here to allow the user to
# supply a custom option.
def select_from_list(
    options,
    things_choosing="choice",
    indentation=2,
    request_confirmation=True,
    sep_char="-",
    max_display_cols=70,
    allow_custom=False,
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

        allow_custom: Whether to allow a free-form custom response.
                      Defaults to False, naturally, but can be useful
                      to include e.g. when selecting plom server
                      directories.
    """

    ### First, we construct the text menu for the user in three parts.
    header = f"Select a {things_choosing}."

    separator = f"{indentation*' '}{(max_display_cols-indentation)*sep_char}"

    # Separate entries with newlines and indent by `indentation` many
    # space characters
    candidate_list = "\n".join(
        [f"{indentation*' '}{i}: {option}" for (i, option) in enumerate(options)]
    )

    if allow_custom:
        # candidate_list += f"\n{indentation*' '}{((max_display_cols-indentation)*'·')}"
        candidate_list += f"\n{indentation*' '}{-1}: <CUSTOM>"

    # For printing AFTER we get the user's input.
    footer = f"\n{max_display_cols*'='}\n\n"

    # Print the combined menu thingy.
    print(f"{header}\n{separator}\n{candidate_list}")

    choice = get_choice_with_validation(
        options, indentation, request_confirmation, separator, allow_custom
    )

    print(footer)

    return choice


def ask_for_confirmation(indentation, choice_index, choice):
    """
    Simple helper function for...requesting confirmation in dialogues
    with the user.

    args:
        indentation: int, number of columns to indent the things
                     printed

        choice_index: int giving the index of the selected option in
                      the list of options presented to the user. Can
                      be -1 if the user opted for custom input (when
                      available)

        choice: The choice_index that the user selected, corresponding
                to `options[choice_index]` in the calling function
                (unless the user gave a custom input)
    """
    if choice_index == -1:  # Customized answer
        print(f"{indentation*' '}You input: {choice}")
        confirmation_response = input(f"{indentation*' '}Confirm custom input? [y/n] ")
    else:  # Noncustomized answer
        print(f"{indentation*' '}You selected {choice_index}: {choice}")
        confirmation_response = input(f"{indentation*' '}Confirm choice? [y/n] ")

    # TODO: Should we default to accepting empty inputs?
    return bool(confirmation_response in ["y", "Y"])


def get_choice_with_validation(
    options, indentation, request_confirmation, separator, allow_custom
):
    """
    Offload the loop from the list selection function above to this
    helper function.

    FIXME: Does this make the code more readable at all? Maybe this is
    unnecessary compartmentalization and we should roll it all back
    into the `select_from_list()` function.
    """

    min_ind = -1 if allow_custom else 0
    max_ind = len(options) - 1

    # OK So this `max_ind + allow_custom` thing here is pretty 900IQ
    # unless I messed it up. Basically, if max_ind == -1, that's OK if
    # we're allowed to do custom-form input because `allow_custom =
    # True` will get implicitly cast to the integer `1` and so we get
    # `max_ind + allow_custom == 0`.
    if (max_ind + allow_custom) < 0:
        # Is this print statement necessary?
        print(f"Nothing available to choose from.")
        return

    # This is implicitly the else case
    while True:
        choice_index = input(f"\n{indentation*' '}Choice [{min_ind}-{max_ind}]: ")
        try:
            # These two lines can trip the exceptions below (this
            # serves as lowkey input verification. We're just vibing
            # here y'all)
            choice_index = int(choice_index)
            assert choice_index >= min_ind and choice_index <= max_ind
            print(separator)

            # This implicitly means we must have `allow_custom=True`
            # by the assertion above
            if choice_index == -1:
                choice = input(f"{indentation*' '}Please input your custom choice: ")
            else:
                choice = options[choice_index]

            proceed = ask_for_confirmation(indentation, choice_index, choice)

            if proceed:
                # Vertically separate from whatever's next
                return choice
            else:
                continue

        except ValueError:
            print("Please respond with a nonnegative integer.")

        except AssertionError:
            if choice_index < min_ind:
                print(f"Choice too small (min is {min_ind}).")
            else:
                print(f"Choice to large (max is {max_ind}).")

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
        print("No assignment selected.")
        return

    return (course, assignment)


def mcd_dir(purpose_string=""):
    """
    mcd --> `m` from `mk`, `c` from `ch`, `d` for `dir`. Basically,
    generate the plom server directories if they don't exist;
    otherwise cd into them.

    Assumes that the current directory is where all of the plom server
    files and such should be deposited. So be sure to put the call to
    `()` inside of some `chdir()` calls if you want files deposited elsewhere.

    kwargs:
        purpose_string: Will get appended to `things_choosing` to
                        explain to the user what the purpose of the
                        subdirectory choice we're making is.

                        TODO: Add an example call

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

    existing_dirs = sorted(
        [_ for _ in os.listdir() if os.path.isdir(_) and _ not in _excluded_dirs]
    )

    target_dir = select_from_list(
        existing_dirs, things_choosing=f"subdir{purpose_string}", allow_custom=True
    )

    # Definitely would be stupid to cast `existing_dirs` to a set
    # for this check but part of me really wants to haha
    if target_dir not in existing_dirs:
        os.mkdir(target_dir)

    os.chdir(target_dir)

    return


def mcd_server_dirs():
    """
    Repeat `mcd_dir()` twice, once to select the class dir, the second
    time to select the assignment dir.

    Return the location of the final plom server dir.
    """
    mcd_dir(purpose_string=" for the class")
    mcd_dir(purpose_string=" for the assignment")
    return os.getcwd()


def test_interactive_directories():
    user = local_login()

    response = interactive_course_selection(user)

    if response is not None:
        (course, assignment) = response

        start_dir = os.getcwd()
        try:
            plom_server_dir = mcd_server_dirs()
        except:  # FIXME: Don't leave this as a bare exception clause!

            print("Yikes you hit an error.")
            print("i ain't reading all that")
            print("i'm happy for u tho")
            print("or sorry that happened")
            os.chdir(start_dir)
            raise


def initialize_plom_server(course, assignment, server_dir):
    """
    Generate the `.toml` file and
    """

    o_dir = os.getcwd()  # original directory

    print("\n\nGetting enrollment data from canvas and building `classlist.csv`...")
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

    print("Temporarily exporting manager password...")
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

    print("Launching plom server.")
    # plom_server = subprocess.Popen(["plom-server", "launch"], stdout=subprocess.DEVNULL)
    plom_server = subprocess.Popen(
        ["plom-server", "launch"],
        stdout=subprocess.DEVNULL,
        preexec_fn=_set_pdeathsig(signal.SIGTERM),  # Linux only?
    )

    print(
        "Server *should* be running now (although hopefully you can't because theoretically output should be suppressed). In light of this, be extra sure to explicitly kill the server (e.g., `pkill plom-server`) before trying to start a new one --- it can persist even after the original python process has been killed.\n\nTo verify if the server is running, you can try the command\n  ss -lntu\nto check if the 41984 port has a listener.\n"
    )

    subprocess.run(["sleep", "3"])

    print("Building classlist...")
    build_class = subprocess.run(
        ["plom-build", "class", "classlist.csv"], capture_output=True
    )

    print("Building the database...")
    build_class = subprocess.run(
        ["plom-build", "make", "--no-pdf"], capture_output=True
    )

    os.chdir(o_dir)

    return plom_server


if __name__ == "__main__":
    test_interactive_directories()

    # print(f"  working directory is now `{os.getcwd()}`")

    # plom_server = initialize(course, assignment)

    # print("\n\ngetting submissions from canvas...")
    # get_submissions(assignment, dry_run=False)

    # print("scanning submissions...")
    # scan_submissions()

    # # Return to starting directory
    # os.chdir(o_dir)
