#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Aidan Murphy

"""Command line tool to start a Plom demonstration server."""

__copyright__ = "Copyright (C) 2018-2025 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from shlex import split
from tempfile import TemporaryDirectory
from time import sleep

from plom.textools import buildLaTeX
from plom_server import __version__

from plom_server.scripts.launch_plom_server import (
    launch_gunicorn_production_server_process,
    launch_django_dev_server_process,
)


# TODO: not a fan of global variables, and mypy needs this to be defined
global demo_files
# so temporarily set it to "."; we'll fix it in main()
demo_files = Path(".")

global _demo_script_launch_time
_demo_script_launch_time: None | float = None


def saytime(comment: str) -> None:
    """Echo information about how long we've been running."""
    global _demo_script_launch_time
    now = time.localtime()

    if _demo_script_launch_time is None:
        _demo_script_launch_time = time.monotonic()
        print(f"\n{time.strftime('%H:%M:%S', now)}: Launching the timer.\n")
    if comment:
        elapsed = time.monotonic() - _demo_script_launch_time
        print(
            f"\n{time.strftime('%H:%M:%S', now)}: "
            f"{comment} "
            f"[{elapsed:.0f} s since launch]\n"
        )

    sys.stdout.flush()
    sys.stderr.flush()


def wait_for_user_to_type_quit() -> None:
    """Wait for correct user input and then return."""
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


def get_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Also used by the sphinx docs: do not rename without changing there.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    The --stop-after and --wait-after options take many possible values.
    If both are omitted, the code behaves like `--wait-after rubrics`.

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
    * randoiding = run rando-id'er to identify papers, will use best predictions to ID papers and else random.  You will need to have the `plom-client` installed.
    * randomarking = several rando-markers are run in parallel to leave comments and annotations on student work.  You will need to have the `plom-client` installed.
    * tagging = (future/not-yet-implemented) = pedagogy tags will be applied to questions to label them with learning goals.
    * spreadsheet = a marking spreadsheet is downloaded.
    * reassembly = marked papers are reassembled (along, optionally, with solutions).
    * reports = (future/not-yet-implemented) = instructor and student reports are built.
    """,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
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
    parser.add_argument("--half-marks", dest="half_marks", action="store_true")
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
        help="Stop the demo sequence at a certain breakpoint. Leave the server running.",
    )
    stop_wait_group.add_argument(
        "--wait-after",
        action="store",
        choices=stop_wait_choices,
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint. Terminate the server.",
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
    return parser


def run_django_manage_command(cmd) -> None:
    """Run the given Django command and wait for return.

    Command must finish successfully (zero return code).

    Args:
        cmd: the command to run.
    """
    full_cmd = get_django_cmd_prefix() + " " + cmd
    subprocess.run(split(full_cmd), check=True)


def run_plom_cli_command(cmd: str) -> None:
    """Run the given plom-cli command and wait for return.

    Command must finish successfully (zero return code).

    Args:
        cmd: the command to run, in a form close to what would be entered
            after `plom-cli` or `python3 -m plom.cli` on the command line.
            The full command will be echoed to stdout.
    """
    cmd = "python3 -m plom.cli " + cmd
    print(f"\nIssuing this command: {cmd}\n")
    # Some gitlab CI environments do not expose plom-cli
    # (but things are in a bad way if python3 -m doesn't work)
    subprocess.run(split(cmd), check=True)


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


def upload_demo_assessment_spec_file() -> None:
    """Upload a demo assessment spec."""
    print("Uploading demo assessment spec")
    spec_file = demo_files / "demo_assessment_spec.toml"
    # run_django_manage_command(f"plom_preparation_spec upload {spec_file}")
    run_plom_cli_command(f"upload-spec {spec_file}")


def _build_with_and_without_soln(source_path: Path) -> None:
    """Build soln and non-soln form of the assessment, writing PDF files into the CWD."""
    source_path_tex = source_path.with_suffix(".tex")
    if not source_path_tex.exists():
        raise ValueError(f"Cannot open file {source_path_tex}")

    # read in the .tex as a big string
    with source_path_tex.open("r") as fh:
        original_data = fh.read()

    # comment out the '\printanswers' line
    no_soln_data = re.sub(r"\\printanswers", r"% \\printanswers", original_data)
    # just the filename, in the CWD
    no_soln_pdf_filename = Path(source_path.stem + ".pdf")
    if no_soln_pdf_filename.exists():
        print(f"  - skipping build of {no_soln_pdf_filename} b/c it already exists")
    else:
        with open(no_soln_pdf_filename, "wb") as f:
            (r, stdouterr) = buildLaTeX(no_soln_data, f)
        if r != 0:
            print(stdouterr)
            raise RuntimeError(
                f"LaTeX build {no_soln_pdf_filename} failed with exit code {r}: "
                "stdout/stderr shown above"
            )
        print(f"  - successfully built {no_soln_pdf_filename}")

    # remove any %-comments on line with '\printanswers'
    yes_soln_data = re.sub(r"%\s+\\printanswers", r"\\printanswers", original_data)
    yes_soln_pdf_filename = Path(source_path.stem + "_solutions.pdf")
    if yes_soln_pdf_filename.exists():
        print(f"  - skipping build of {yes_soln_pdf_filename} b/c it already exists")
    else:
        with open(yes_soln_pdf_filename, "wb") as f:
            (r, stdouterr) = buildLaTeX(yes_soln_data, f)
        if r != 0:
            print(stdouterr)
            raise RuntimeError(
                f"LaTeX build {yes_soln_pdf_filename} failed with exit code {r}: "
                "stdout/stderr shown above"
            )
        print(f"  - successfully built {yes_soln_pdf_filename}")


def build_demo_assessment_source_pdfs() -> None:
    """Build the demo source PDF files."""
    print("Building assessment / solution source pdfs from tex in temp dirs")
    for filename in ("assessment_v1", "assessment_v2", "assessment_v3"):
        _build_with_and_without_soln(demo_files / filename)


def upload_demo_assessment_source_files():
    """Upload demo assessment source pdfs."""
    print("Uploading demo assessment source pdfs")
    for v in (1, 2, 3):
        source_pdf = f"assessment_v{v}.pdf"
        # run_django_manage_command(f"plom_preparation_source upload -v {v} {source_pdf}")
        run_plom_cli_command(f"upload-source {source_pdf} -v {v}")


def upload_demo_solution_files():
    """Use 'plom_solution_spec' to upload demo solution spec and source pdfs."""
    print("Uploading demo solution spec")
    soln_spec_path = demo_files / "demo_solution_spec.toml"
    print("Uploading demo solution pdfs")
    run_django_manage_command(f"plom_soln_spec upload {soln_spec_path}")
    for v in [1, 2, 3]:
        soln_pdf_path = f"assessment_v{v}_solutions.pdf"
        run_django_manage_command(f"plom_soln_sources upload -v {v} {soln_pdf_path}")


def upload_demo_classlist(length="normal", prename=True):
    """Upload a classlist for the demo."""
    if length == "long":
        cl_path = demo_files / "cl_for_long_demo.csv"
    elif length == "plaid":
        cl_path = demo_files / "cl_for_plaid_demo.csv"
    elif length == "quick":
        cl_path = demo_files / "cl_for_quick_demo.csv"
    else:  # for normal
        cl_path = demo_files / "cl_for_demo.csv"

    run_plom_cli_command("delete-classlist")
    # run_django_manage_command(f"plom_preparation_classlist upload {cl_path}")
    run_plom_cli_command(f"upload-classlist {cl_path}")

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
        * (sources): upload the source pdfs
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

    saytime("Users created.")

    if stop_after == "users":
        print("Stopping after users created.")
        return False

    upload_demo_assessment_spec_file()

    saytime("Assessment specification is uploaded.")

    if stop_after == "spec":
        print("Stopping after assessment specification uploaded.")
        return False

    build_demo_assessment_source_pdfs()
    upload_demo_assessment_source_files()
    if solutions:
        upload_demo_solution_files()
    upload_demo_classlist(length, prename)

    saytime("Finished uploading assessment sources and classlist.")

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

    saytime("Finished populating the database and tweaking the qvmap.")

    if stop_after == "populate":
        print("Stopping after paper-database populated.")
        return False

    build_all_papers_and_wait()

    saytime("Finished building the papers.")

    if stop_after == "papers-built":
        print("Stopping after papers_built.")
        return False
    # download a zip of all the papers.
    download_zip()

    # now set preparation status as done
    # note that this also creates system rubrics and
    # builds substitute page images
    print("Setting papers are printed")
    run_django_manage_command("plom_preparation_status --set finished")
    print("For testing purposes, set papers are not printed and then set it again.")
    run_django_manage_command("plom_preparation_status --set todo")
    run_django_manage_command("plom_preparation_status --set finished")

    saytime("")

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
    # delete the first bundle and upload it again so that we exercise
    # that part of the code-base.
    print("For testing purposes, delete first bundle and upload it again.")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action delreup")
    run_django_manage_command("plom_staging_bundles wait")
    # now trigger reading of qr-codes
    run_django_manage_command(f"plom_demo_bundles --length {length} --action read")
    run_django_manage_command("plom_staging_bundles wait")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action map_hw")


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
        muck = whether or not to "muck" with the mock bundles - this is intended to imitate the effects of poor scanning. Not yet functional.

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
    """Run the auto ID reader."""
    run_django_manage_command("plom_run_id_reader --run")
    run_django_manage_command("plom_run_id_reader --wait")


def _ensure_client_available():
    try:
        # tell MyPy to ignore this for testing
        import plomclient  # type: ignore[import-not-found]
        from plomclient.client import __version__ as clientversion  # type: ignore
    except ImportError as err:
        print("*" * 64)
        print()
        raise RuntimeError(
            "The randoiding and randomarking utilities depend on plom-client, "
            f"which is not installed:\n  {err}.\n"
            "Either install plom-client, or stop the demo earlier."
        ) from None
    print(
        f"Good we have plom-client installed, version {clientversion},"
        f" found at {plomclient}"
    )


def run_the_randoider(*, port):
    """Run the rando-IDer.

    All papers will be ID'd after this call.
    """
    _ensure_client_available()

    # TODO: hardcoded http://
    srv = f"http://localhost:{port}"
    # list of markers and their passwords
    users = [
        ("demoMarker1", "demoMarker1"),
    ]

    cmd = f"python3 -m plomclient.client.randoIDer -s {srv} -u {users[0][0]} -w {users[0][1]} --use-predictions"
    print(f"RandoIDing!  calling: {cmd}")
    subprocess.check_call(split(cmd))


def run_the_randomarker(*, port, half_marks=False):
    """Run the rando-Marker.

    All papers will be marked after this call.
    """
    _ensure_client_available()

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
        cmd = f"python3 -m plomclient.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial {X[2]} --download-rubrics"
        if half_marks:
            cmd += " --allow-half"
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
        cmd = f"python3 -m plomclient.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial 100"
        print(f"RandoMarking!  calling: {cmd}")
        subprocess.check_call(split(cmd))


def push_demo_rubrics():
    """Push demo rubrics from toml."""
    # note - hard coded question range here.
    for question_idx in (1, 2, 3, 4):
        rubric_toml = demo_files / f"demo_assessment_rubrics_q{question_idx}.toml"
        run_django_manage_command(f"plom_rubrics push manager {rubric_toml}")


def create_and_link_question_tags():
    """Create the demo question tags and link them to some questions."""
    qtags_csv = demo_files / "demo_assessment_qtags.csv"
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


def run_marking_commands(*, port: int, stop_after=None, half_marks=False) -> bool:
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
        half_marks = whether or not to use +/- half-mark rubrics

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    # add rubrics, question-tags and then run the randomaker.
    # add system rubrics first, then push the demo ones from toml
    if half_marks:
        print("Using +/- 0.5 rubrics")
        run_django_manage_command("plom_rubrics half manager")
    push_demo_rubrics()
    if stop_after == "rubrics":
        return False

    create_and_link_question_tags()
    if stop_after == "qtags":
        return False

    run_the_auto_id_reader()
    if stop_after == "auto-id":
        return False

    run_the_randoider(port=port)
    if stop_after == "randoiding":
        return False

    run_the_randomarker(port=port, half_marks=half_marks)
    if stop_after == "randomarking":
        return False

    return True


def run_finishing_commands(*, stop_after=None, solutions=True) -> bool:
    """Run the finishing commands."""
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
    print(">> Future plom dev will include student-reports download here.")
    return True


def main():
    """The Plom demo script."""
    saytime("")  # Launch the chatty timer.

    args = get_parser().parse_args()

    # cast stop-after, wait-after from list of options to a singleton or None
    if args.stop_after:
        stop_after = args.stop_after[0]
        wait_at_end = False
    else:
        wait_at_end = True
        if args.wait_after:
            stop_after = args.wait_after[0]
        else:
            # default if no stop/wait after specified
            stop_after = "rubrics"

    if not args.development and not args.port:
        print("You must supply a port for the production server.")

    # TODO: I guess?
    os.environ["DJANGO_SETTINGS_MODULE"] = "plom_server.settings"
    # TODO: needed for plom-cli, not entirely comfortable with the hardcoding here
    os.environ["PLOM_SERVER"] = f"http://localhost:{args.port}"
    os.environ["PLOM_USERNAME"] = "manager"
    os.environ["PLOM_PASSWORD"] = "1234"

    # we specify this directory relative to the plom_server
    global demo_files
    # TODO: better to just port all of this to importlib.resources
    import plom_server

    (_path,) = plom_server.__path__
    demo_files = Path(_path) / "demo_files/"

    assert demo_files.exists(), "cannot continue w/o demo files"

    # clean out old db and misc files, then rebuild blank db
    run_django_manage_command("plom_clean_all_and_build_db")

    saytime("Finished refreshing the database.")

    # build the user-groups and the admin and manager users
    run_django_manage_command("plom_make_groups_and_first_users")
    # build extra-page and scrap-paper PDFs
    run_django_manage_command("plom_build_scrap_extra_pdfs")

    run_django_manage_command("plom_get_static_javascript")

    saytime("Finished making groups and early users, extra pages, and scrap paper.")

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
        sleep(0.25)
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

            saytime("Launching scanning process ...")
            print(">> Scanning of papers")
            if not run_demo_bundle_scan_commands(
                length=args.length,
                stop_after=stop_after,
                muck=args.muck,
                versioned_id=args.versioned_id,
            ):
                break

            print("*" * 50)
            saytime("Launching marking process ...")
            print(">> Ready for marking")
            if not run_marking_commands(
                port=args.port, stop_after=stop_after, half_marks=args.half_marks
            ):
                break

            print("*" * 50)
            print(">> Ready for finishing")
            saytime("Launching finishing process ....")
            run_finishing_commands(stop_after=stop_after, solutions=args.solutions)
            break

        if args.development:
            saytime("Development server is running, with all setup complete.")
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
        saytime("Cleanup commands all issued. Stopping now.")
        print("^" * 50)


if __name__ == "__main__":
    main()
