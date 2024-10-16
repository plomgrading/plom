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

    The stdout and stderr of the process will be merged into the
    usual stdout and stderr.

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
    # perhaps unnecessary?
    # return subprocess.Popen(split(full_cmd), stdout=sys.stdout, stderr=sys.stderr)
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


def launch_huey_process() -> list[subprocess.Popen]:
    """Launch the Huey-consumer for processing background tasks."""
    print("Launching Huey queues as background jobs.")
    return [
        popen_django_manage_command("djangohuey --queue tasks"),
        popen_django_manage_command("djangohuey --queue parentchores"),
    ]


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

    If the WEB_CONCURRENCY environment variable is set, we use that many
    worker processes.  Otherwise we use a default value (currently 2).

    Args:
        port: the port for the server.

    Returns:
        Open ``Popen`` on the gunicorn process.
    """
    print("Launching Gunicorn web-server.")
    # TODO - put in an 'are we in production' check.
    num_workers = os.environ.get("WEB_CONCURRENCY", 2)
    cmd = f"gunicorn Web_Plom.wsgi --workers {num_workers}"

    # TODO: temporary increase to 60s by default, Issue #3676
    timeout = os.environ.get("PLOM_GUNICORN_TIMEOUT", 180)
    cmd += f" --timeout {timeout}"

    # TODO: long-term code here:
    # timeout = os.environ.get("PLOM_GUNICORN_TIMEOUT", "")
    # # just omit and use gunicorn's default if unspecified
    # if timeout:
    #     cmd += f" --timeout {timeout}"

    cmd += f" --bind 0.0.0.0:{port}"
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
        # TODO: Issue #3577 remove later?
        run_django_manage_command("plom_build_scrap_extra_pdfs")
    else:
        # clean out old db and misc files, then rebuild blank db
        run_django_manage_command("plom_clean_all_and_build_db")
        # build the user-groups and the admin and manager users
        run_django_manage_command("plom_make_groups_and_first_users")
        # build extra-page and scrap-paper PDFs
        run_django_manage_command("plom_build_scrap_extra_pdfs")

    if not args.development:
        run_django_manage_command("collectstatic --clear --no-input")

    # now put main things inside a try/finally so that we
    # can clean up the Huey/server processes on exit.
    huey_process, server_process = None, None
    try:
        print("v" * 50)
        huey_processes = launch_huey_process()
        if args.development:
            server_process = launch_django_dev_server_process(port=args.port)
        else:
            server_process = launch_gunicorn_production_server_process(port=args.port)
        # processes still running after small delay? probably working
        time.sleep(0.25)
        for hp in huey_processes:
            r = hp.poll()
            if r is not None:
                raise RuntimeError(f"Problem with Huey process {hp.pid}: exit code {r}")
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
        for hp in huey_processes:
            hp.terminate()
        if server_process:
            server_process.terminate()
        print("^" * 50)
