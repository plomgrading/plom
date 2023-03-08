# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import shutil
from pathlib import Path
from shlex import split
import subprocess
from time import sleep

from demo import scribble_on_exams


def recreate_postgres_db():
    import psycopg

    with psycopg.connect(user="postgres", password="postgres", autocommit=True) as conn:
        print("Removing old database.")
        try:
            with conn.cursor() as curs:
                curs.execute("DROP DATABASE plom_db;")
        except psycopg.errors.InvalidCatalogName:
            print("No database 'plom_db' - continuing")

        print("Creating database 'plom_db'");
        try:
            with conn.cursor() as curs:
                curs.execute("CREATE DATABASE plom_db;")
        except psycopg.errors.DuplicateDatabase:
            with conn.cursor() as curs:
                print("We should not reach here.")
                quit()


def remove_old_migration_files():
    print("Avoid perplexing errors by removing autogen migration droppings")

    for path in Path(".").glob("**/migrations/*.py"):
        if path.name == "__init__.py":
            continue
        else:
            print(f"Removing {path}")
            path.unlink(missing_ok=True)


def remove_old_db_and_misc_user_files():
    print("Removing old DB and any misc user-generated files")

    for fname in [
        "db.sqlite3",
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


def rebuild_migrations_and_migrate():
    print("Rebuild the database migrations and migrate")
    for cmd in ["makemigrations", "migrate"]:
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def make_groups_and_users():
    print("Create groups and users")
    for cmd in ["plom_create_groups", "plom_create_demo_users"]:
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def prepare_assessment():
    print("Prepare assessment: ")
    print(
        "\tUpload demo spec, upload source pdfs and classlist, enable prenaming, and generate qv-map"
    )
    for cmd in [
        "plom_demo_spec",
        "plom_preparation_test_source upload -v 1 useful_files_for_testing/test_version1.pdf",
        "plom_preparation_test_source upload -v 2 useful_files_for_testing/test_version2.pdf",
        "plom_preparation_prenaming --enable",
        "plom_preparation_classlist upload useful_files_for_testing/cl_for_demo.csv",
        "plom_preparation_qvmap generate",
    ]:
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def launch_huey_workers():
    print("Launching huey workers for background tasks")
    for cmd in ["djangohuey"]:
        py_man_cmd = f"python3 manage.py {cmd}"
        return subprocess.Popen(split(py_man_cmd))


def launch_server():
    print("Launching django server")
    for cmd in ["runserver 8000"]:
        py_man_cmd = f"python3 manage.py {cmd}"
        return subprocess.Popen(split(py_man_cmd))


def build_db_and_papers():
    print("Populating database in background")
    for cmd in [
        "plom_papers build_db",
        "plom_preparation_extrapage --build",
        "plom_build_papers --start-all",
    ]:
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def wait_for_papers_to_be_ready():
    py_man_ep = "python3 manage.py plom_preparation_extrapage"
    py_man_papers = "python3 manage.py plom_build_papers --status"
    ep_todo = True
    papers_todo = True

    sleep(2)
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
            print("Still waiting for pdf production tasks. Sleeping 2 seconds.")
            sleep(2)
        else:
            print("Extra page and papers all built - continuing to next step of demo.")
            break


def download_zip():
    print("Download a zip of all the papers")
    cmd = "plom_build_papers --download-all"
    py_man_cmd = f"python3 manage.py {cmd}"
    subprocess.check_call(split(py_man_cmd))


def upload_bundles():
    # TODO quick hack workaround for Issue #2578
    for n in [1, 2, 3]:
        cmd = f"plom_staging_bundles upload demoScanner{1} fake_bundle{n}.pdf"
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))
        print("For time being sleep between bundle uploads. TODO = fix this")
        sleep(5)


def read_qr_codes():
    # TODO quick hack workaround for Issue #2578
    todo = [1, 2, 3]
    while True:
        done = []
        for n in todo:
            cmd = f"plom_staging_bundles read_qr fake_bundle{n}"
            py_man_cmd = f"python3 manage.py {cmd}"
            out_qr = subprocess.check_output(split(py_man_cmd),stderr=subprocess.STDOUT).decode("utf-8")
            if "has been read" in out_qr:
                done.append(n)
        for n in done:
            todo.remove(n)
        if len(todo)>0:
            print(f"Stil waiting for {len(todo)} bundles to process - sleep between attempts")
            sleep(5)
        else:
            print("QR-codes of all bundles read.")
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


def main():
    recreate_postgres_db()
    
    print("*" * 40)
    remove_old_migration_files()

    print("*" * 40)
    remove_old_db_and_misc_user_files()

    print("*" * 40)
    rebuild_migrations_and_migrate()

    print("*" * 40)
    make_groups_and_users()

    print("*" * 40)
    prepare_assessment()

    print("*" * 40)
    build_db_and_papers()

    print("*" * 40)
    server_proc = launch_server()

    print("*" * 40)
    huey_worker_proc = launch_huey_workers()

    print("v" * 40)
    print("Everything is now up and running")
    print("^" * 40)

    wait_for_papers_to_be_ready()
    print("*" * 40)

    download_zip()
    print("*" * 40)

    scribble_on_exams()

    print("*" * 40)
    upload_bundles()
    print("*" * 40)
    read_qr_codes()


    wait_for_exit()

    print("v" * 40)
    clean_up_processes([huey_worker_proc, server_proc])
    print("Demo complete")
    print("^" * 40)


if __name__ == "__main__":
    main()
