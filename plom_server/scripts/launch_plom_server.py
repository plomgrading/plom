#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald

"""Command line tool to start a Plom server."""

__copyright__ = "Copyright (C) 2018-2026 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import os
import subprocess
import time
from shlex import split

from plom_server import __version__
from plom_server.Base.services import database_service


def get_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Also used by the sphinx docs: do not rename without changing there.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "--hotstart",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="""
            By default, attempt to hotstart the server using existing
            data, if such data is found.  Note the detection is not
            perfect and currently no verification of integrity between
            database and media is performed.

            If False, refuse to start if there appears to be data in
            place.  You will have to remove the data for the server to
            start in this case.
        """,
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="""
            Remove all database, media and other data before starting.
            Be careful with this!
        """,
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
    return parser


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


def get_django_cmd_prefix() -> str:
    """Return the basic command to be used to run Django commands."""
    if os.environ.get("DJANGO_SETTINGS_MODULE"):
        return "django-admin"
    return "python3 manage.py"


def launch_huey_processes() -> list[subprocess.Popen]:
    """Launch the Huey-consumer for processing background chores."""
    print("Launching Huey queues as background chores.")
    return [
        popen_django_manage_command("djangohuey --queue chores"),
        popen_django_manage_command("djangohuey --queue parentchores"),
    ]


def launch_django_dev_server_process(*, port: int | None = None) -> subprocess.Popen:
    """Launch Django's native development server.

    Note that this should never be used in production.

    Keyword Args:
        port: the port for the server, or a default if omitted.
    """
    # TODO - put in an 'are we in production' check.

    # this needs to be run in the background
    print("Launching Django development server.")
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def launch_gunicorn_production_server_process(
    *, port: int | None = None
) -> subprocess.Popen:
    """Launch the Gunicorn web server.

    Note that this should always be used in production.

    If the WEB_CONCURRENCY environment variable is set, we use that many
    worker processes.  Otherwise we use a default value (currently 2).

    Keyword Args:
        port: the port for the server.  Defaults to 8000 if omitted.

    Returns:
        Open ``Popen`` on the gunicorn process.
    """
    print("Launching Gunicorn web-server.")
    # TODO - put in an 'are we in production' check.
    num_workers = int(os.environ.get("WEB_CONCURRENCY", 2))
    cmd = f"gunicorn plom_server.wsgi --workers {num_workers}"

    # TODO: temporary increase to 60s by default, Issue #3676
    timeout = os.environ.get("PLOM_GUNICORN_TIMEOUT", 180)
    cmd += f" --timeout {timeout}"

    # TODO: long-term code here:
    # timeout = os.environ.get("PLOM_GUNICORN_TIMEOUT", "")
    # # just omit and use gunicorn's default if unspecified
    # if timeout:
    #     cmd += f" --timeout {timeout}"

    if port is None:
        port = 8000
    # TODO: I'm inclined to omit this --bind altogether, as gunicorn defaults to 8000
    # But is there some important Container-related reason to specify 0.0.0.0 here?
    # (the Gunicorn default is 127.0.0.1:8000, see Issue #3918)
    cmd += f" --bind 0.0.0.0:{port}"
    return subprocess.Popen(split(cmd))


def wait_for_user_to_type_quit() -> None:
    """Wait for correct user input and then return."""
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


def main():
    """The Plom server script."""
    # TODO: I guess?
    os.environ["DJANGO_SETTINGS_MODULE"] = "plom_server.settings"

    args = get_parser().parse_args()

    # Note: run_django_manage_command("plom_database --check-for-database") has no
    # return value, so we call the service directly (isn't this better anyway?)
    have_db = database_service.is_there_a_database()

    if have_db and not args.wipe:
        if not args.hotstart:
            raise ValueError(
                "There is an existing database: consider passing --hotstart or --wipe"
            )
        print("DOING A HOT START (we already have a database)")
        print("Issue #3299: Please note this merely checks for the *existence* of")
        print("a database; it does not yet check anything about the filesystem.")
    else:
        # We either don't have a DB or we do and we want to wipe it.
        # clean out old db and misc files, then rebuild blank db
        run_django_manage_command("plom_clean_all_and_build_db")
        # build the user-groups and the admin and manager users
        run_django_manage_command("plom_make_groups_and_first_users")
        # build extra-page and scrap-paper PDFs
        run_django_manage_command("plom_build_scrap_extra_pdfs")

        run_django_manage_command("plom_get_static_javascript")

        if not args.development:
            run_django_manage_command("collectstatic --clear --no-input")

    # now put main things inside a try/finally so that we
    # can clean up the Huey/server processes on exit.
    huey_processes, server_process = None, None
    try:
        print("v" * 50)
        huey_processes = launch_huey_processes()
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


if __name__ == "__main__":
    main()
