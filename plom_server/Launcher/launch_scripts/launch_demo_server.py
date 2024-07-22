#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import argparse
from pathlib import Path
from shlex import split
import subprocess


# sigh.... python dependent import - sorry.
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

# we specify this directory relative to the plom_server
# root directory, rather than getting Django things up and
# running, just to get at these useful files.

demo_file_directory = Path("./Launcher/launch_scripts/demo_files/")


def wait_for_user_to_type_quit() -> None:
    """Wait for correct user input and then return."""
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


def set_argparse_and_get_args() -> argparse.Namespace:
    """Configure argparse to collect commandline options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Port number on which to launch server")
    parser.add_argument(
        "--length",
        action="store",
        choices=["quick", "normal", "long", "plaid"],
        default="normal",
        help="Describe length of demo",
    )
    parser.add_argument(
        "--solutions",
        default=True,
        action="store_true",
        help="Upload solutions to demo server",
    )
    parser.add_argument("--no-solutions", dest="solutions", action="store_false")
    parser.add_argument(
        "--prename",
        default=True,
        action="store_true",
        help="Prename papers as determined by the demo classlist",
    )
    parser.add_argument("--no-prename", dest="prename", action="store_false")
    parser.add_argument(
        "--muck",
        default=True,
        action="store_true",
        help="Run pdf-mucking to simulate poor scanning of papers",
    )
    parser.add_argument("--no-muck", dest="muck", action="store_false")
    parser.add_argument(
        "--stop-after",
        action="store",
        choices=[
            "users",
            "spec",
            "sources",
            "populate",
            "papers_built",
            "bundles-created",
            "bundles-read",
            "bundles-pushed",
        ],
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint.",
    )
    return parser.parse_args()


def run_django_manage_command(cmd) -> None:
    """Run the given command with 'python3 manage.py' and wait for return.

    Args:
        cmd: the command to run.
    """
    full_cmd = "python3 manage.py " + cmd
    subprocess.run(split(full_cmd))


def popen_django_manage_command(cmd) -> subprocess.Popen:
    """Run the given command with 'python3 manage.py' using process Popen and return a handle to the process.

    Args:
        cmd: the command to run.

    Returns a subprocess.Popen class that can be used to terminate the background command.
    """
    full_cmd = "python3 manage.py " + cmd
    return subprocess.Popen(split(full_cmd))


def confirm_run_from_correct_directory() -> None:
    """Confirm that the script is being run from the directory containing django's manage.py command."""
    if not Path("./manage.py").exists():
        raise RuntimeError(
            "This script needs to be run from the same directory as django's manage.py script."
        )


def pre_launch():
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
    if port:
        print(f"Dev server will run on port {args.port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def upload_demo_assessment_spec_file():
    """Use 'plom_preparation_test_spec' to upload a demo assessment spec."""
    print("Uploading demo assessment spec")
    spec_file = demo_file_directory / "demo_assessment_spec.toml"
    run_django_manage_command(f"plom_preparation_test_spec upload {spec_file}")


def upload_demo_test_source_files():
    """Use 'plom_preparation_source' to upload a demo assessment source pdfs."""
    print("Uploading demo assessment source pdfs")
    for v in [1, 2]:
        source_pdf = demo_file_directory / f"source_version{v}.pdf"
        run_django_manage_command(f"plom_preparation_source upload -v {v} {source_pdf}")


def upload_demo_solution_files():
    """Use 'plom_solution_spec' to upload demo solution spec and source pdfs."""
    print("Uploading demo solution spec")
    soln_spec_path = demo_file_directory / "demo_solution_spec.toml"
    print("Uploading demo solution pdfs")
    run_django_manage_command(f"plom_soln_spec upload {soln_spec_path}")
    for v in [1, 2]:
        soln_pdf_path = demo_file_directory / f"solutions{v}.pdf"
        run_django_manage_command(f"plom_soln_sources upload -v {v} {soln_pdf_path}")


def upload_demo_classlist(length="normal", prename=True):
    """Use 'plom_preparation_classlist' to the appropriate classlist for the demo."""
    if length == "long":
        cl_path = demo_file_directory / "cl_for_long_demo.csv"
    elif length == "plaid":
        cl_path = demo_file_directory / "cl_for_plaid_demo.csv"
    elif length == "quick":
        cl_path = demo_file_directory / "cl_for_quick_demo.csv"
    else:  # for normal
        cl_path = demo_file_directory / "cl_for_demo.csv"

    run_django_manage_command(f"plom_preparation_classlist upload {cl_path}")

    if prename:
        run_django_manage_command("plom_preparation_prenaming --enable")
    else:
        run_django_manage_command("plom_preparation_prenaming --disable")


def populate_the_database(length="normal"):
    """Use 'plom_papers' to build a qv-map for the demo and populate the database."""
    production = {"quick": 35, "normal": 70, "long": 600, "plaid": 2000}
    print(
        f"Building a question-version map and populating the database with {production[length]} papers"
    )
    run_django_manage_command(
        f"plom_papers build_db -n {production[length]} --first-paper 1"
    )
    print("Paper database is now populated")


def build_all_papers_and_wait():
    """Trigger build all the printable paper pdfs and wait for completion."""
    from time import sleep

    run_django_manage_command("plom_build_papers --start-all")
    # since this is a background huey job, we need to
    # wait until all those pdfs are actually built -
    # we can get that by looking at output from plom_build_papers --status
    pdf_status_cmd = "python3 manage.py plom_build_papers --count-done"
    while True:
        out_papers = subprocess.check_output(split(pdf_status_cmd)).decode("utf-8")
        if "all" in out_papers.casefold():
            break
        else:
            print(out_papers.strip())
            sleep(1)
    print("All paper PDFs are now built.")


def run_demo_preparation_commands(
    *, length="normal", stop_after=None, solutions=True, prename=True
):
    """Run commands to prepare a demo assessment.

    In order it runs:
        * (users): create demo users,
        * (spec): upload the demo spec,
        * (sources): upload the test-source pdfs
            >> will also upload solutions at this point if instructed by user
            >> will also upload the classlist
        * (populate): make the qv-map and populate the database
        * (papers_built): make the paper-pdfs
        * finally - set preparation as completed.

    KWargs:
        length = the length of the demo: quick, normal, long, plaid.
        stop_after = after which step should the demo be stopped, see list above.
        solutions = whether or not to upload solutions as part of the demo.
        prename = whether or not to prename some papers in the demo.
    """
    # in order the demo will

    # TODO = remove this demo-specific command
    run_django_manage_command("plom_create_demo_users")
    if stop_after == "users":
        print("Stopping after users created.")
        return

    run_django_manage_command("plom_demo_spec")
    if stop_after == "spec":
        print("Stopping after assessment specification uploaded.")
        return

    upload_demo_test_source_files()
    if solutions:
        upload_demo_solution_files()
    upload_demo_classlist(length, prename)
    if stop_after == "sources":
        print("Stopping after assessment sources and classlist uploaded.")
        return

    populate_the_database(length)
    if stop_after == "populate":
        print("Stopping after paper-database populated.")
        return

    build_all_papers_and_wait()
    if stop_after == "papers_built":
        print("Stopping after papers_built.")
        return

    # now set preparation status as done
    run_django_manage_command("plom_preparation_status --set finished")

    return


def download_zip() -> None:
    """Use 'plom_build_papers' to download a zip of all paper-pdfs."""
    run_django_manage_command("plom_build_papers --download-all")
    print("Downloaded a zip of all the papers")


def _read_bundle_config(length):
    # read the config toml file
    if length == "quick":
        fname = "bundle_for_quick_demo.toml"
    elif length == "long":
        fname = "bundle_for_long_demo.toml"
    elif length == "plaid":
        fname = "bundle_for_plaid_demo.toml"
    else:
        fname = "bundle_for_demo.toml"
    with open(demo_file_directory / fname, "rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as e:
            raise RuntimeError(e)


def build_bundles(length="normal"):
    """Create bundles of papers to simulate scanned student papers.

    KWargs:
        length = the length of the demo.
    """

    bundle_config_dict = _read_bundle_config(length)
    # HACKED UP TO HERE
    print(bundle_config_dict)


def run_demo_bundle_scan_commands(*, stop_after=None, length="normal", muck=False):
    """Run commands to step through the scanning process in the demo.

    In order it runs:
        * (bundles_created): create bundles of papers; system will also make random annotations on these papers to simulate student work. (Optionally) the system will "muck" the papers to simulate poor scanning.
            >> will also download a zip of all build papers from which mock-bundles are created.
    KWargs:
        stop_after = after which step should the demo be stopped, see list above.
        length = the length of the demo: quick, normal, long, plaid.
        muck = whether or not to "muck" with the mock test bundles - this is intended to imitate the effects of poor scanning.
    """
    download_zip()
    build_bundles(length)
    if stop_after == "bundles_created":
        return


if __name__ == "__main__":
    args = set_argparse_and_get_args()
    # cast stop-after from list of options to a singleton or None
    if args.stop_after:
        stop_after = args.stop_after[0]
    else:
        stop_after = None

    build_bundles(length=args.length)
    quit()

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

        print("*" * 50)
        print("> Running demo specific commands")
        print(">> Preparation of assessment")
        run_demo_preparation_commands(
            length=args.length,
            stop_after=stop_after,
            solutions=args.solutions,
            prename=args.prename,
        )
        print(">> Scanning of papers")
        run_demo_bundle_scan_commands(stop_after=stop_after, muck=args.muck)
        print("*" * 50)
        wait_for_user_to_type_quit()

    finally:
        print("v" * 50)
        print("Shutting down huey and django dev server")
        huey_process.terminate()
        server_process.terminate()
        print("^" * 50)
