# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

"""Plom django demo.

For testing, debugging and development.
"""

import argparse
import os
from pathlib import Path
from shlex import split
import shutil
import subprocess
from time import sleep

from django.core.management import call_command
from django.conf import settings

from demo import scribble_on_exams, make_hw_bundle
from demo import remove_old_migration_files

from plom import __version__


def get_database_engine():
    """Which database engine are we using?"""

    from Web_Plom import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgres" in engine:
        return "postgres"
    elif "sqlite" in engine:
        return "sqlite"
    else:
        return "unknown"
    # TODO = get this working with mysql too


def recreate_postgres_db():
    import psycopg2

    # use local "socket" thing
    # conn = psycopg2.connect(user="postgres", password="postgres")
    # use TCP/IP
    host = settings.DATABASES["postgres"]["HOST"]
    conn = psycopg2.connect(user="postgres", password="postgres", host=host)

    conn.autocommit = True
    print("Removing old database.")
    try:
        with conn.cursor() as curs:
            curs.execute("DROP DATABASE plom_db;")
    except psycopg2.errors.InvalidCatalogName:
        print("No database 'plom_db' - continuing")

    print("Creating database 'plom_db'")
    try:
        with conn.cursor() as curs:
            curs.execute("CREATE DATABASE plom_db;")
    except psycopg2.errors.DuplicateDatabase:
        with conn.cursor() as curs:
            print("We should not reach here.")
            quit()
    conn.close()


def remove_old_db_and_misc_user_files(engine):
    print("Removing old DB and any misc user-generated files")

    if engine == "sqlite":
        Path("db.sqlite3").unlink(missing_ok=True)
    elif engine == "postgres":
        recreate_postgres_db()
    else:
        raise RuntimeError('Unexpected engine "{engine}"')

    for fname in [
        "fake_bundle1.pdf",
        "fake_bundle2.pdf",
        "fake_bundle3.pdf",
    ]:
        Path(fname).unlink(missing_ok=True)

    for path in Path("huey").glob("huey_db.*"):
        path.unlink(missing_ok=True)

    for rmdir in ["sourceVersions", "papersToPrint", "media"]:
        shutil.rmtree(rmdir, ignore_errors=True)

    Path("media").mkdir()


def sqlite_set_wal():
    import sqlite3

    print("Setting journal mode WAL for sqlite database")
    conn = sqlite3.connect("db.sqlite3")
    conn.execute("pragma journal_mode=wal")
    conn.close()


def rebuild_migrations_and_migrate(engine):
    # print("Rebuild the database migrations and migrate")
    # for cmd in ["makemigrations", "migrate"]:
    # py_man_cmd = f"python3 manage.py {cmd}"
    # subprocess.check_call(split(py_man_cmd))

    call_command("makemigrations")
    call_command("migrate")

    if engine == "sqlite":
        sqlite_set_wal()


def make_groups_and_users():
    print("Create groups and users")
    call_command("plom_create_groups")
    call_command("plom_create_demo_users")


def prepare_assessment():
    print("Prepare assessment: ")
    print(
        "\tUpload demo spec, upload source pdfs and classlist, enable prenaming, and generate qv-map"
    )
    call_command("plom_demo_spec")
    call_command(
        "plom_preparation_test_source",
        "upload",
        "-v 1",
        "useful_files_for_testing/test_version1.pdf",
    )
    call_command(
        "plom_preparation_test_source",
        "upload",
        "-v 2",
        "useful_files_for_testing/test_version2.pdf",
    )
    call_command("plom_preparation_prenaming", enable=True)
    call_command(
        "plom_preparation_classlist",
        "upload",
        "useful_files_for_testing/cl_for_demo.csv",
    )
    call_command("plom_preparation_qvmap", "generate")


def launch_huey_workers():
    # I don't understand why, but this seems to need to be run as a sub-proc
    # and not via call_command... maybe because it launches a bunch of background
    # stuff?

    print("Launching huey workers for background tasks")
    for cmd in ["djangohuey --quiet"]:  # quiet huey tasks.
        py_man_cmd = f"python3 manage.py {cmd}"
        return subprocess.Popen(split(py_man_cmd))


def launch_server():
    print("Launching django server")
    # this needs to be run in the background
    cmd = "python3 manage.py runserver 8000"
    return subprocess.Popen(split(cmd))


def build_db_and_papers():
    print("Populating database in background")
    call_command("plom_papers", "build_db")
    call_command("plom_preparation_extrapage", "build")
    call_command("plom_build_papers", "--start-all")


def wait_for_papers_to_be_ready():
    py_man_ep = "python3 manage.py plom_preparation_extrapage"
    py_man_papers = "python3 manage.py plom_build_papers --status"
    ep_todo = True
    papers_todo = True

    sleep(1)
    while True:
        if ep_todo:
            out_ep = subprocess.check_output(split(py_man_ep)).decode("utf-8")
            if "complete" in out_ep:
                print("Extra page is built")

                ep_todo = False
        if papers_todo:
            out_papers = subprocess.check_output(split(py_man_papers)).decode("utf-8")
            if "All papers are now built" in out_papers:
                print("Papers are now built.")
                papers_todo = False
        if papers_todo or ep_todo:
            print("Still waiting for pdf production tasks. Sleeping.")
            sleep(1)
        else:
            print("Extra page and papers all built - continuing to next step of demo.")
            break


def download_zip():
    print("Download a zip of all the papers")
    cmd = "plom_build_papers --download-all"
    py_man_cmd = f"python3 manage.py {cmd}"
    subprocess.check_call(split(py_man_cmd))


def upload_bundles(number_of_bundles=3, homework_bundles={}):
    bundle_names = [f"fake_bundle{n+1}.pdf" for n in range(number_of_bundles)]
    # these will be messed with before upload via the --demo toggle
    for bname in bundle_names:
        cmd = f"plom_staging_bundles upload demoScanner{1} {bname} --demo"
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))
        sleep(0.2)
    # we don't want to mess with these - just upload them
    hw_bundle_names = [
        f"fake_hw_bundle_{paper_number}.pdf" for paper_number in homework_bundles
    ]
    for bname in hw_bundle_names:
        cmd = f"plom_staging_bundles upload demoScanner{1} {bname}"
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))
        sleep(0.2)


def wait_for_upload(number_of_bundles=3, homework_bundles={}):
    bundle_names = [f"fake_bundle{n+1}" for n in range(number_of_bundles)]
    for paper_number in homework_bundles:
        bundle_names.append(f"fake_hw_bundle_{paper_number}")

    for bname in bundle_names:
        cmd = f"plom_staging_bundles status {bname}"
        py_man_cmd = f"python3 manage.py {cmd}"
        while True:
            out = subprocess.check_output(split(py_man_cmd)).decode("utf-8")
            if "qr-codes not yet read" in out:
                print(f"{bname} ready for qr-reading")
                break
            else:
                print(out)
            sleep(0.5)


def read_qr_codes(number_of_bundles=3):
    for n in range(1, number_of_bundles + 1):
        cmd = f"plom_staging_bundles read_qr fake_bundle{n}"
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))
        sleep(0.5)


def map_homework_pages(homework_bundles={}):
    print("Mapping homework pages to questions")
    for paper_number, question_list in homework_bundles.items():
        bundle_name = f"fake_hw_bundle_{paper_number}"
        print(
            f"Assigning pages in {bundle_name} to paper {paper_number} questions {question_list}"
        )
        call_command(
            "plom_paper_scan",
            "map",
            bundle_name,
            "-t",
            paper_number,
            "-q",
            str(question_list),
        )
        sleep(0.5)


def wait_for_qr_read(number_of_bundles=3):
    for n in range(1, number_of_bundles + 1):
        cmd = f"plom_staging_bundles status fake_bundle{n}"
        py_man_cmd = f"python3 manage.py {cmd}"
        while True:
            out = subprocess.check_output(split(py_man_cmd)).decode("utf-8")
            if "qr-codes not yet read" in out:
                print(f"fake_bundle{n}.pdf still being read")
                print(out)
                sleep(0.5)
            else:
                print(f"fake_bundle{n}.pdf has been read")
                break


def push_if_ready(number_of_bundles=3):
    todo = [k + 1 for k in range(number_of_bundles)]
    while True:
        done = []
        for n in todo:
            cmd = f"plom_staging_bundles status fake_bundle{n}"
            py_man_cmd = f"python3 manage.py {cmd}"
            out_stat = subprocess.check_output(
                split(py_man_cmd), stderr=subprocess.STDOUT
            ).decode("utf-8")
            if "perfect" in out_stat:
                push_cmd = f"python3 manage.py plom_staging_bundles push fake_bundle{n}"
                subprocess.check_call(split(push_cmd))
                done.append(n)
                sleep(1)
        for n in done:
            todo.remove(n)
        if len(todo) > 0:
            print(
                f"Still waiting for {len(todo)} bundles to process - sleep between attempts"
            )
            sleep(1)
        else:
            print("All bundles pushed.")
            break


def wait_for_exit():
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


def clean_up_processes(procs):
    print("Terminating background processes")
    for proc in procs:
        proc.terminate()


def configure_django_stuff():
    from django import setup

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Web_Plom.settings")
    setup()


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="""
            Run as usual but stop immediately if everything worked.
            Without this option, wait until "quit" is typed before exiting.
        """,
    )
    parser.add_argument(
        "--startserver",
        action="store_true",
        help="""
            Start the server in as minimal a configuration as possible
            and then stop.
            TODO: maybe not working correctly yet.
        """,
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="""
            Scan the papers to the staging error but don't push.
        """,
    )
    parser.add_argument(
        "--readqr",
        action="store_true",
        help="""
            Scan the papers, read QR codes, but don't push.
        """,
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="""
            Configure, scan, read QR codes, and finally push papers to
            the server.
            This is currently the default and should be ready for
            grading with the client.
        """,
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    huey_worker_proc, server_proc = _doit(args)

    if not args.test:
        wait_for_exit()
    sleep(0.1)
    print("v" * 40)
    clean_up_processes([huey_worker_proc, server_proc])
    print("Demo complete")
    print("^" * 40)


def _doit(args):
    number_of_bundles = 5
    homework_bundles = {
        61: [[1], [2], [], [2, 3], [3]],
        62: [[1], [1, 2], [2], [], [3]],
        63: [[1, 2], [3], []],
    }

    configure_django_stuff()

    engine = get_database_engine()
    print(f"You appear to be running with a {engine} DB.")

    print("*" * 40)
    if engine == "postgres":
        recreate_postgres_db()

    print("*" * 40)
    remove_old_migration_files()

    print("*" * 40)
    remove_old_db_and_misc_user_files(engine)

    print("*" * 40)
    rebuild_migrations_and_migrate(engine)

    print("*" * 40)
    make_groups_and_users()

    # launch the huey workers before building db
    # and associated PDF-build tasks (which need huey)
    print("*" * 40)
    huey_worker_proc = launch_huey_workers()

    # TODO: I get errors if I move this after launching the server...
    print("*" * 40)
    prepare_assessment()

    print("*" * 40)
    server_proc = launch_server()

    if args.startserver:
        return (huey_worker_proc, server_proc)

    print("*" * 40)
    build_db_and_papers()

    wait_for_papers_to_be_ready()
    print("*" * 40)

    download_zip()
    print("*" * 40)

    scribble_on_exams(
        number_of_bundles=number_of_bundles,
        extra_page_papers=[49, 50],
        garbage_page_papers=[1, 2],
        duplicate_pages={1: 3, 2: 6},
        duplicate_qr=[3, 4],
        wrong_version=[5, 6],
    )
    for paper_number, question_list in homework_bundles.items():
        make_hw_bundle(paper_number, question_list=question_list)

    print("*" * 40)
    upload_bundles(
        number_of_bundles=number_of_bundles, homework_bundles=homework_bundles
    )

    wait_for_upload(
        number_of_bundles=number_of_bundles,
    )

    if args.scan:
        return (huey_worker_proc, server_proc)

    print("*" * 40)
    read_qr_codes(
        number_of_bundles=number_of_bundles,
    )
    map_homework_pages(homework_bundles=homework_bundles)

    print("*" * 40)
    wait_for_qr_read(
        number_of_bundles=number_of_bundles,
    )

    if args.readqr:
        return (huey_worker_proc, server_proc)

    # print("*" * 40)
    # push_if_ready()
    call_command("plom_staging_bundles", "status")
    call_command("plom_staging_bundles", "push", "fake_bundle2")

    call_command("plom_rubrics", "init")
    call_command("plom_rubrics", "push", "--demo")

    # if args.push:
    #     return
    return (huey_worker_proc, server_proc)


if __name__ == "__main__":
    main()
