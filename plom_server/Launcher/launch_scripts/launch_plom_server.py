#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

import argparse
import os
from pathlib import Path
from shlex import split
import subprocess
import time


def run_django_manage_command(cmd: str) -> None:
    """Run the given Django command and wait for return.

    Args:
        cmd: the command to run.
    """
    full_cmd = get_django_cmd_prefix() + " " + cmd
    subprocess.run(split(full_cmd), check=True)


def popen_django_manage_command(cmd: str) -> subprocess.Popen:
    """Run the given Django command using a process Popen and return a handle to the process.

    Args:
        cmd: the command to run.

    Returns:
        A subprocess.Popen class that can be used to terminate the
        background command.  You'll probably want to do some checking
        that the process is up, as it could fail almost instantly
        following this command.  Or at any time really.

    Raises:
        OSError: such as FileNotFoundError if the command cannot be
            found.  But note lack of failure here is no guarantee
            the process is still running at any later time; such is
            the nature of inter-process communication.
    """
    full_cmd = get_django_cmd_prefix() + " " + cmd
    return subprocess.Popen(split(full_cmd))


def confirm_run_from_correct_directory() -> None:
    """Confirm appropriate env vars are set or the current directory contains Django's manage.py."""
    # Perhaps later, things will work from other locations
    # if os.environ.get("DJANGO_SETTINGS_MODULE"):
    #     return None
    if not Path("./manage.py").exists():
        raise RuntimeError(
            "This script needs to be run from the same directory as Django's manage.py script."
        )


def get_django_cmd_prefix() -> str:
    """Return the basic command to be used to run Django commands."""
    if os.environ.get("DJANGO_SETTINGS_MODULE"):
        return "django-admin"
    return "python3 manage.py"


def pre_launch(*, devel: bool = False) -> None:
    """Run commands required before the plom-server can be launched.

    Keyword Args:
        devel: True if this to be a development server.

    Note that this runs:
        * plom_clean_all_and_build_db: cleans out any old database and misc user-generated file, then rebuilds the blank db.
        * plom_make_groups_and_first_users: creates user-groups needed by plom, and an admin user and a manager-user.
        * plom_build_scrap_extra_pdfs: build the scrap-paper and extra-page pdfs.
        * Django's collectstatic command to put files in a static dir and
          possibly use a different server for them.

    Note that this can easily be extended in the future to run more commands as required.
    """
    # start by cleaning out the old db and misc files.
    run_django_manage_command("plom_clean_all_and_build_db")
    # build the user-groups and the admin and manager users
    run_django_manage_command("plom_make_groups_and_first_users")
    # build extra-page and scrap-paper PDFs
    run_django_manage_command("plom_build_scrap_extra_pdfs")
    if not devel:
        run_django_manage_command("collectstatic --clear --no-input")


def launch_huey_process() -> subprocess.Popen:
    """Launch the Huey-consumer for processing background tasks.

    Note that this runs the Django manage command 'djangohuey --quiet'.
    """
    print("Launching Huey.")
    # this needs to be run in the background
    return popen_django_manage_command("djangohuey --quiet")


def launch_django_dev_server_process(*, port: int | None = None) -> subprocess.Popen:
    """Launch Django's native development server.

    Note that this should never be used in production.

    KWargs:
        port: the port for the server.
    """
    # TODO - put in an 'are we in production' check.

    # this needs to be run in the background
    print("Launching Django development server.")
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def launch_gunicorn_production_server_process(port: int) -> subprocess.Popen:
    """Launch the Gunicorn web server.

    Note that this should always be used in production.

    Args:
        port: the port for the server.
    """
    print("Launching Gunicorn web-server.")
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
        "--hot-start",
        action="store_true",
        help="Attempt to start Huey and the server using existing data.",
    )
    parser.add_argument("--port", help="Port number on which to launch server")
    prod_dev_group = parser.add_mutually_exclusive_group()
    prod_dev_group.add_argument(
        "--development",
        action="store_true",
        help="""
            Run the Django development webserver.
            Not intended for use in production.
        """,
    )
    prod_dev_group.add_argument(
        "--production",
        action="store_false",
        dest="development",
        help="Run a production Gunicorn server (default).",
    )
    args = parser.parse_args()

    if not args.development and not args.port:
        print("You must supply a port for the production server.")

    # make sure we are in the correct directory to run things.
    confirm_run_from_correct_directory()
    # clean up and rebuild things before launching.
    if args.hot_start:
        print("Attempting a hot-start of the server and Huey.")
    else:
        pre_launch(devel=args.development)
    # now put main things inside a try/finally so that we
    # can clean up the Huey/server processes on exit.
    huey_process, server_process = None, None
    try:
        print("v" * 50)
        huey_process = launch_huey_process()
        if args.development:
            server_process = launch_django_dev_server_process(port=args.port)
        else:
            server_process = launch_gunicorn_production_server_process(port=args.port)
        # both processes still running after small delay? probably working
        time.sleep(0.25)
        r = huey_process.poll()
        if r is not None:
            raise RuntimeError(f"Problem with Huey process: exit code {r}")
        r = server_process.poll()
        if r is not None:
            raise RuntimeError(f"Problem with server process: exit code {r}")
        print("^" * 50)

        if args.development:
            wait_for_user_to_type_quit()
        else:
            print("Running production server, will not quit on user-input.")
            server_process.wait()

    finally:
        print("v" * 50)
        print("Shutting down Huey and Django dev server")
        if huey_process:
            huey_process.terminate()
        if server_process:
            server_process.terminate()
        print("^" * 50)
