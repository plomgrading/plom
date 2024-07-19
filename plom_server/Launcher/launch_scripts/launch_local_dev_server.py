# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

import argparse
from pathlib import Path
from shlex import split
import subprocess


def run_django_manage_command(cmd) -> None:
    full_cmd = "python3 manage.py " + cmd
    subprocess.run(split(full_cmd))


def popen_django_manage_command(cmd) -> subprocess.Popen:
    full_cmd = "python3 manage.py " + cmd
    return subprocess.Popen(split(full_cmd))


def confirm_run_from_correct_directory():
    if not Path("./manage.py").exists():
        raise RuntimeError(
            "This script needs to be run from the same directory as django's manage.py script."
        )


def pre_launch():
    # start by cleaning out the old db and misc files.
    run_django_manage_command("plom_clean_all_and_build_db")
    # build the user-groups and the admin and manager users
    run_django_manage_command("plom_make_groups_and_first_users")
    # build extra-page and scrap-paper PDFs
    run_django_manage_command("plom_build_scrap_extra_pdfs")


def launch_huey_process():
    # this needs to be run in the background
    return popen_django_manage_command("djangohuey --quiet")


def launch_django_dev_server_process(*, port: int | None = None):
    # this needs to be run in the background
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def wait_for_user_to_type_quit() -> None:
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Port number on which to launch server")
    args = parser.parse_args()

    # make sure we are in the correct directory to run things.
    confirm_run_from_correct_directory()
    # clean up and rebuild things before launching.
    pre_launch()
    # now put main things inside a try/finally so that we
    # can clean up the huey/server processes on exit.
    try:
        print("v" * 50)
        print("Launching huey and django dev server")
        huey_process = launch_huey_process()
        server_process = launch_django_dev_server_process(port=args.port)
        print("^" * 50)
        wait_for_user_to_type_quit()

    finally:
        print("v" * 50)
        print("Shutting down huey and django dev server")
        huey_process.terminate()
        server_process.terminate()
        print("^" * 50)
