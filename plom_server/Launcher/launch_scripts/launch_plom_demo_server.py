#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from shlex import split
import subprocess
import time
from tempfile import TemporaryDirectory

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
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
    The --stop-after and --wait-after options take many possible values.

    * users = the basic plom-system (server, db, etc) are set up, and demo-users are created.
    * spec = a demo assessment specification is uploaded.
    * sources = demo assessment sources are uploaded. Also a classlist and (if selected) solutions.
    * populate = the database is populated with papers.
    * papers-built = assessment PDFs are created from the sources.
    * bundles-created = PDF bundles are created to simulate scanned student work.
    * bundles-uploaded = those PDF bundles are uploaded and their qr-codes read (but not processed further).
    * bundles-pushed = those bundles are "pushed" so that they can be graded.
    * rubrics = system and demo rubrics are created for marking.
    * qtags = demo question-tags are created.
    * auto-id = run the auto-id-reader
    * randoiding = run rando-id'er to identify papers, will use best predictions to ID papers and else random.
    * randomarking = several rando-markers are run in parallel to leave comments and annotations on student work.
    * tagging = (future/not-yet-implemented) = pedagogy tags will be applied to questions to label them with learning goals.
    * spreadsheet = a marking spreadsheet is downloaded.
    * reassembly = marked papers are reassembled (along, optionally, with solutions).
    * reports = (future/not-yet-implemented) = instructor and student reports are built.
    """,
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port number on which to launch server"
    )
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
    parser.add_argument("--versioned-id", dest="versioned_id", action="store_true")
    parser.add_argument(
        "--muck",
        default=True,
        action="store_true",
        help="Run pdf-mucking to simulate poor scanning of papers (not functional yet)",
    )
    parser.add_argument("--no-muck", dest="muck", action="store_false")
    stop_wait_choices = [
        "users",
        "spec",
        "sources",
        "populate",
        "papers-built",
        "bundles-created",
        "bundles-uploaded",
        "bundles-pushed",
        "rubrics",
        "qtags",
        "auto-id",
        "randoiding",
        "randomarking",
        "tagging",
        "spreadsheet",
        "reassembly",
        "reports",
    ]
    stop_wait_group = parser.add_mutually_exclusive_group()
    stop_wait_group.add_argument(
        "--stop-after",
        action="store",
        choices=stop_wait_choices,
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint.",
    )
    stop_wait_group.add_argument(
        "--wait-after",
        action="store",
        choices=stop_wait_choices,
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint.",
    )
    prod_dev_group = parser.add_mutually_exclusive_group()
    prod_dev_group.add_argument(
        "--development",
        action="store_true",
        default=True,
        help="""
            Run the Django development webserver
            (this is the default for the demo
            but do not use this in production)."
        """,
    )
    prod_dev_group.add_argument(
        "--production",
        action="store_false",
        dest="development",
        help="Run a production Gunicorn server.",
    )

    return parser.parse_args()


def run_django_manage_command(cmd) -> None:
    """Run the given Django command and wait for return.

    Command must finish successfully (zero return code).

    Args:
        cmd: the command to run.
    """
    full_cmd = get_django_cmd_prefix() + " " + cmd
    subprocess.run(split(full_cmd), check=True)


def popen_django_manage_command(cmd) -> subprocess.Popen:
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

    print("Launching Django development server.")
    # this needs to be run in the background
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def launch_gunicorn_production_server_process(port: int) -> subprocess.Popen:
    """Launch the Gunicorn web server.

    Note that for production, this should be used instead of Django's
    built-in development server.

    If the WEB_CONCURRENCY environment variable is set, we use that many
    worker processes.  Otherwise we use a default value (currently 2).

    Args:
        port: the port for the server.

    Returns:
        Open ``Popen`` on the gunicorn process.
    """
    print("Launching Gunicorn web-server.")
    # TODO - put in an 'are we in production' check.
    num_workers = int(os.environ.get("WEB_CONCURRENCY", 2))
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


def upload_demo_assessment_spec_file():
    """Use 'plom_preparation_test_spec' to upload a demo assessment spec."""
    print("Uploading demo assessment spec")
    spec_file = demo_file_directory / "demo_assessment_spec.toml"
    run_django_manage_command(f"plom_preparation_test_spec upload {spec_file}")


def build_demo_test_source_pdfs() -> None:
    print("Building assessment / solution source pdfs from tex")
    # assumes that everything needed is in the demo_file_directory
    subprocess.run(
        ["python3", "build_plom_assessment_pdfs.py"],
        cwd=demo_file_directory,
        check=True,
    )


def upload_demo_test_source_files():
    """Use 'plom_preparation_source' to upload a demo assessment source pdfs."""
    print("Uploading demo assessment source pdfs")
    for v in (1, 2, 3):
        source_pdf = demo_file_directory / f"assessment_v{v}.pdf"
        run_django_manage_command(f"plom_preparation_source upload -v {v} {source_pdf}")


def upload_demo_solution_files():
    """Use 'plom_solution_spec' to upload demo solution spec and source pdfs."""
    print("Uploading demo solution spec")
    soln_spec_path = demo_file_directory / "demo_solution_spec.toml"
    print("Uploading demo solution pdfs")
    run_django_manage_command(f"plom_soln_spec upload {soln_spec_path}")
    for v in [1, 2, 3]:
        soln_pdf_path = demo_file_directory / f"assessment_v{v}_solutions.pdf"
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
    """Use 'plom_qvmap' to build a qv-map for the demo and populate the database."""
    production = {"quick": 35, "normal": 70, "long": 600, "plaid": 1200}
    print(
        f"Building a question-version map and populating the database with {production[length]} papers"
    )
    run_django_manage_command(
        f"plom_qvmap build_db -n {production[length]} --first-paper 1"
    )
    print("Paper database is now populated")


def download_the_qvmap(filepath: Path):
    """Use 'plom_qvmap' to download the qv-map."""
    print("Downloading the question-version map")
    run_django_manage_command(f"plom_qvmap download {filepath}")


def depopulate_the_database():
    """Use 'plom_qvmap' to clear the qv-map and database.

    Note - runs in foreground; blocks until completed.
    """
    print("Clearing the database and qv-map")
    run_django_manage_command("plom_qvmap clear")


def read_hack_and_resave_qvmap(filepath: Path):
    """Read qvmap file, set odd rows id.version to 2, resave.

    Note - we do not use version 3 id page at all.
    """
    with open(filepath) as fh:
        reader = csv.DictReader(fh)
        qvmap_rows = [row for row in reader]
    # even paper numbers should get id-version 3
    for n, row in enumerate(qvmap_rows):
        if int(row["paper_number"]) % 2 == 0:
            qvmap_rows[n]["id.version"] = 3
    headers = list(qvmap_rows[0].keys())
    with open(filepath, "w") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in qvmap_rows:
            writer.writerow(row)


def upload_the_qvmap(filepath: Path):
    """Use 'plom_qvmap' to upload the qv-map."""
    print("Uploading the question-version map")
    run_django_manage_command(f"plom_qvmap upload {filepath}")


def build_all_papers_and_wait():
    """Trigger build all the printable paper pdfs and wait for completion."""
    from time import sleep

    run_django_manage_command("plom_build_paper_pdfs --start-all")
    # since this is a background Huey job, we need to
    # wait until all those pdfs are actually built -
    # we can get that by looking at output from plom_build_paper_pdfs --status
    pdf_status_cmd = get_django_cmd_prefix() + " plom_build_paper_pdfs --count-done"
    while True:
        out_papers = subprocess.check_output(split(pdf_status_cmd)).decode("utf-8")
        if "all" in out_papers.casefold():
            break
        else:
            print(out_papers.strip())
            sleep(1)
    print("All paper PDFs are now built.")


def download_zip() -> None:
    """Use 'plom_build_paper_pdfs' to download a zip of all paper-pdfs."""
    run_django_manage_command("plom_build_paper_pdfs --download-all")
    print("Downloaded a zip of all the papers")


def run_demo_preparation_commands(
    *,
    length="normal",
    stop_after=None,
    solutions=True,
    prename=True,
    versioned_id=False,
) -> bool:
    """Run commands to prepare a demo assessment.

    In order it runs:
        * (users): create demo users,
        * (spec): upload the demo spec,
        * (sources): upload the test-source pdfs
            >> will also upload solutions at this point if instructed by user
            >> will also upload the classlist
        * (populate): make the qv-map and populate the database
        * (papers-built): make the paper-pdfs
        * finally - download a zip of all the papers, and set preparation as completed.

    KWargs:
        length = the length of the demo: quick, normal, long, plaid.
        stop_after = after which step should the demo be stopped, see list above.
        solutions = whether or not to upload solutions as part of the demo.
        prename = whether or not to prename some papers in the demo.
        versioned_id = whether or not to use multiple versions of the id pages.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    # in order the demo will

    # TODO = remove this demo-specific command
    run_django_manage_command("plom_create_demo_users")
    run_django_manage_command("plom_leadmarker_membership --toggle demoMarker1")
    run_django_manage_command("plom_leadmarker_membership --toggle demoMarker2")
    if stop_after == "users":
        print("Stopping after users created.")
        return False

    upload_demo_assessment_spec_file()
    if stop_after == "spec":
        print("Stopping after assessment specification uploaded.")
        return False

    build_demo_test_source_pdfs()
    upload_demo_test_source_files()
    if solutions:
        upload_demo_solution_files()
    upload_demo_classlist(length, prename)
    if stop_after == "sources":
        print("Stopping after assessment sources and classlist uploaded.")
        return False

    populate_the_database(length)
    # if using multiple versions of the id page, then
    # after populating, download the qvmap, clear the db,
    # hack the qvmap and then upload the new qvmap.
    if versioned_id:
        with TemporaryDirectory() as tdir:
            tmp_qv_path = Path(tdir) / "tmp_qv_filename.csv"
            download_the_qvmap(tmp_qv_path)
            depopulate_the_database()
            read_hack_and_resave_qvmap(tmp_qv_path)
            upload_the_qvmap(tmp_qv_path)

    if stop_after == "populate":
        print("Stopping after paper-database populated.")
        return False

    build_all_papers_and_wait()
    if stop_after == "papers-built":
        print("Stopping after papers_built.")
        return False
    # download a zip of all the papers.
    download_zip()

    # now set preparation status as done
    # note that this also creates system rubrics
    run_django_manage_command("plom_preparation_status --set finished")

    return True


def build_the_bundles(length="normal", versioned_id=False):
    """Create bundles of papers to simulate scanned student papers.

    Note: takes the pdf of each paper directly from the file
        system, not the downloaded zip. The bundles are then
        saved in the current directory.

    KWargs:
        length = the length of the demo.
        versioned_id = whether using multiple versions of id-page
    """
    if versioned_id:
        run_django_manage_command(
            f"plom_demo_bundles --length {length} --action build --versioned-id"
        )
    else:
        run_django_manage_command(f"plom_demo_bundles --length {length} --action build")


def upload_the_bundles(length="normal"):
    """Uploads the demo bundles from the working directory.

    Note that this waits for the uploads to process and then also
    triggers the qr-code reading and waits for that to finish.

    KWargs:
        length = the length of the demo.
    """
    run_django_manage_command(f"plom_demo_bundles --length {length} --action upload")
    run_django_manage_command("plom_staging_bundles wait")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action read")
    run_django_manage_command("plom_staging_bundles wait")


def push_the_bundles(length):
    """Pushes the demo bundles from staging to the server.

    Only pushes 'perfect' bundles (those without errors). It
    also IDs any (pushed) homework bundles.
    """
    run_django_manage_command(f"plom_demo_bundles --length {length} --action push")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action id_hw")


def run_demo_bundle_scan_commands(
    *,
    stop_after=None,
    length="normal",
    muck=False,
    versioned_id=False,
) -> bool:
    """Run commands to step through the scanning process in the demo.

    In order it runs:
        * (bundles-created): create bundles of papers; system will also make random annotations on these papers to simulate student work. (Optionally) the system will "muck" the papers to simulate poor scanning.
        * (bundles-uploaded): upload the bundles and read their qr-codes
        * finally - push the bundles and id any homework bundles.

    KWargs:
        stop_after = after which step should the demo be stopped, see list above.
        length = the length of the demo: quick, normal, long, plaid.
        muck = whether or not to "muck" with the mock test bundles - this is intended to imitate the effects of poor scanning. Not yet functional.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    build_the_bundles(length, versioned_id=versioned_id)
    if stop_after == "bundles-created":
        return False

    upload_the_bundles(length)
    if stop_after == "bundles-uploaded":
        return False

    push_the_bundles(length)
    if stop_after == "bundles-pushed":
        return False

    return True


def run_the_auto_id_reader():
    run_django_manage_command("plom_run_id_reader --run")
    run_django_manage_command("plom_run_id_reader --wait")


def run_the_randoider(*, port):
    """Run the rando-IDer.

    All papers will be ID'd after this call.
    """
    # TODO: hardcoded http://
    srv = f"http://localhost:{port}"
    # list of markers and their passwords
    users = [
        ("demoMarker1", "demoMarker1"),
    ]

    cmd = f"python3 -m plom.client.randoIDer -s {srv} -u {users[0][0]} -w {users[0][1]} --use-predictions"
    print(f"RandoIDing!  calling: {cmd}")
    subprocess.check_call(split(cmd))


def run_the_randomarker(*, port):
    """Run the rando-Marker.

    All papers will be marked after this call.
    """
    from time import sleep

    # TODO: hardcoded http://
    srv = f"http://localhost:{port}"
    # list of markers and their passwords and percentage to mark
    users = [
        ("demoMarker1", "demoMarker1", 100),
        ("demoMarker2", "demoMarker2", 75),
        ("demoMarker3", "demoMarker3", 75),
        ("demoMarker4", "demoMarker4", 50),
        ("demoMarker5", "demoMarker5", 50),
    ]

    randomarker_processes = []
    for X in users[1:]:
        cmd = f"python3 -m plom.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial {X[2]} --download-rubrics"
        print(f"RandoMarking!  calling: {cmd}")
        randomarker_processes.append(subprocess.Popen(split(cmd)))
        sleep(0.5)
    # now wait for those markers
    while True:
        poll_values = [X.poll() for X in randomarker_processes]
        # check for errors = non-zero non-None return values
        for pv in poll_values:
            if pv not in [0, None]:
                raise subprocess.SubprocessError(
                    "One of the rando-marker processes finished with a non-zero exit status."
                )
        if any(X is None for X in poll_values):
            # we are still waiting on a rando-marker.
            sleep(2)
        else:  # all rando-markers are done
            break

    # now a final run to do any remaining tasks
    for X in users[:1]:
        cmd = f"python3 -m plom.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial 100"
        print(f"RandoMarking!  calling: {cmd}")
        subprocess.check_call(split(cmd))


def push_demo_rubrics():
    # push demo rubrics from toml
    # note - hard coded question range here.
    for question_idx in (1, 2, 3, 4):
        rubric_toml = (
            demo_file_directory / f"demo_assessment_rubrics_q{question_idx}.toml"
        )
        run_django_manage_command(f"plom_rubrics push manager {rubric_toml}")


def create_and_link_question_tags():
    qtags_csv = demo_file_directory / "demo_assessment_qtags.csv"
    # upload question-tags as user "manager"
    run_django_manage_command(f"upload_qtags_csv {qtags_csv} manager")
    # link questions to tags as user "manager"
    # WARNING - HARDCODED LIST
    for tag, question_idx in [
        ("limits", 1),
        ("derivatives", 2),
        ("derivatives", 3),
        ("applications", 3),
        ("applications", 4),
    ]:
        run_django_manage_command(
            f"link_question_with_tag {question_idx} {tag} manager"
        )


def run_marking_commands(*, port: int, stop_after=None) -> bool:
    """Run commands to step through the marking process in the demo.

    In order it runs:
        * (rubrics): Make system and demo rubrics.
        * (qtags): Make and apply question/pedagogy-tags
        * (auto-id): Run the auto id-reader and wait for its results
        * (randoder): make random id-er on papers (this will use the best predictions to id.)
        * (randomarker): make random marking-annotations on papers.

    KWargs:
        stop_after = after which step should the demo be stopped, see list above.
        port = the port on which the demo is running.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    # add rubrics, question-tags and then run the randomaker.
    # add system rubrics first, then push the demo ones from toml
    push_demo_rubrics()
    if stop_after == "rubrics":
        return False

    create_and_link_question_tags()
    if stop_after == "qtags":
        return False

    run_the_auto_id_reader()
    if stop_after == "auto-id":
        return False

    run_the_randoider(port=args.port)
    if stop_after == "randoiding":
        return False

    run_the_randomarker(port=args.port)
    if stop_after == "randomarking":
        return False

    return True


def run_finishing_commands(*, stop_after=None, solutions=True) -> bool:
    print("Reassembling all marked papers.")
    run_django_manage_command("plom_reassemble")
    run_django_manage_command("plom_reassemble --wait")
    # if errors, status has non-zero return code, raising an exception
    run_django_manage_command("plom_reassemble --status")
    if solutions:
        print("Constructing individual solution pdfs for students.")
        run_django_manage_command("plom_build_all_soln")

    if stop_after == "reassembly":
        return False

    print("Downloading a csv of student marks.")
    run_django_manage_command("plom_download_marks_csv")
    if stop_after == "spreadsheet":
        return False

    print(">> Future plom dev will include instructor-report download here.")
    print(">> Future plom dev will include strudent-reports download here.")
    return True


if __name__ == "__main__":
    args = set_argparse_and_get_args()
    # cast stop-after, wait-after from list of options to a singleton or None
    if args.stop_after:
        stop_after = args.stop_after[0]
        wait_at_end = False
    else:
        wait_at_end = True
        if args.wait_after:
            stop_after = args.wait_after[0]
        else:
            stop_after = None

    if not args.development and not args.port:
        print("You must supply a port for the production server.")

    # make sure we are in the correct directory to run things.
    confirm_run_from_correct_directory()

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

        print("*" * 50)
        print("> Running demo specific commands")
        print(">> Preparation of assessment")
        while True:
            if not run_demo_preparation_commands(
                length=args.length,
                stop_after=stop_after,
                solutions=args.solutions,
                prename=args.prename,
                versioned_id=args.versioned_id,
            ):
                break

            print(">> Scanning of papers")
            if not run_demo_bundle_scan_commands(
                length=args.length,
                stop_after=stop_after,
                muck=args.muck,
                versioned_id=args.versioned_id,
            ):
                break

            print("*" * 50)
            print(">> Ready for marking")
            if not run_marking_commands(port=args.port, stop_after=stop_after):
                break

            print("*" * 50)
            print(">> Ready for finishing")
            run_finishing_commands(stop_after=stop_after, solutions=args.solutions)
            break

        if args.development:
            if wait_at_end:
                wait_for_user_to_type_quit()
            else:
                print("Demo process finished.")
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
