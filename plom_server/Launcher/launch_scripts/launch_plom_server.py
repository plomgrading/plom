#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import argparse
from pathlib import Path
from shlex import split
import subprocess


def run_django_manage_command(cmd: str) -> None:
    """Run the given command with 'python3 manage.py' and waits for return.

    Args:
        cmd: the command to run.
    """
    full_cmd = "python3 manage.py " + cmd
    subprocess.run(split(full_cmd))


def popen_django_manage_command(cmd: str) -> subprocess.Popen:
    """Run the given command with 'python3 manage.py' using process Popen and return a handle to the process.

    Args:
        cmd: the command to run.

    Returns a subprocess.Popen class that can be used to terminate the background command.
    """
    full_cmd = "python3 manage.py " + cmd
    return subprocess.Popen(split(full_cmd))


def confirm_run_from_correct_directory() -> None:
    """Confirm the script is being run from the directory containing django's manage.py command."""
    if not Path("./manage.py").exists():
        raise RuntimeError(
            "This script needs to be run from the same directory as django's manage.py script."
        )


def pre_launch() -> None:
    """Run commands required before the plom-server can be launched.

    Note that this runs:
        * plom_clean_all_and_build_db: cleans out any old database and misc user-generated file, then rebuilds the blank db.
        * plom_make_groups_and_first_users: creates user-groups needed by plom, and an admin user and a manager-user.
        * plom_build_scrap_extra_pdfs: build the scrap-paper and extra-page pdfs.

    Note that this can easily be extended in the future to run more commands as required.
    """
    # start by cleaning out the old db and misc files.
    run_django_manage_command("plom_clean_all_and_build_db")
    # build the user-groups and the admin and manager users
    run_django_manage_command("plom_make_groups_and_first_users")
    # build extra-page and scrap-paper PDFs
    run_django_manage_command("plom_build_scrap_extra_pdfs")


def launch_huey_process() -> subprocess.Popen:
    """Launch the huey-consumer for processing background tasks.

    Note that this runs the django manage command 'djangohuey --quiet'.
    """
    print("Launching huey.")
    # this needs to be run in the background
    return popen_django_manage_command("djangohuey --quiet")


def launch_django_dev_server_process(*, port: int | None = None) -> subprocess.Popen:
    """Launch django's native development server.

    Note that this should never be used in production.

    KWargs:
        port: the port for the server.
    """
    # TODO - put in an 'are we in production' check.

    # this needs to be run in the background
    print("Launching django's development server.")
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def launch_gunicorn_production_server_process(port: int) -> subprocess.Popen:
    """Launch the gunicorn web server.

    Note that this should always be used in production.

    Args:
        port: the port for the server.
    """
    print("Launching gunicorn web-server.")
    # TODO - put in an 'are we in production' check.
    cmd = f"gunicorn Web_Plom.wsgi --bind 0.0.0.0:{port}"
    return subprocess.Popen(split(cmd))


def wait_for_user_to_type_quit() -> None:
    """Wait for correct user input and then return."""
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hot-restart", help="Attempt a hot-restart of huey and the server."
    )
    parser.add_argument("--port", help="Port number on which to launch server")
    prod_dev_group = parser.add_mutually_exclusive_group()
    prod_dev_group.add_argument(
        "--development",
        action="store_true",
        help="Run the django development webserver - definitely do not use in production.",
    )
    prod_dev_group.add_argument(
        "--production", action="store_true", help="Run a production gunicorn server."
    )
    args = parser.parse_args()

    if args.production and not args.port:
        print("You must supply a port for the production server.")

    # make sure we are in the correct directory to run things.
    confirm_run_from_correct_directory()
    # clean up and rebuild things before launching.
    if args.hot_restart:
        print("Attempting a hot-restart of the server and huey.")
    else:
        pre_launch()
    # now put main things inside a try/finally so that we
    # can clean up the huey/server processes on exit.
    huey_process, server_process = None, None
    try:
        print("v" * 50)
        huey_process = launch_huey_process()
        if args.production:
            server_process = launch_gunicorn_production_server_process(port=args.port)
        else:
            server_process = launch_django_dev_server_process(port=args.port)
        print("^" * 50)
        if args.development:
            wait_for_user_to_type_quit()
        else:
            print("Running production server, will not quit on user-input.")
            while True:
                pass

    finally:
        print("v" * 50)
        print("Shutting down huey and django dev server")
        if huey_process:
            huey_process.terminate()
        if server_process:
            server_process.terminate()
        print("^" * 50)