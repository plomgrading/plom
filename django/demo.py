# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

import shutil
from pathlib import Path
from shlex import split
import subprocess
from time import sleep


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
    Path("db.sqlite3").unlink(missing_ok=True)
    for path in Path("huey").glob("huey_db.*"):
        path.unlink(missing_ok=True)
    for rmdir in ["sourceVersions", "papersToPrint", "media"]:
        shutil.rmtree(rmdir, ignore_errors=True)
    Path("media").mkdir()


def rebuild_migrations_and_migrate():
    print("Rebuild the database migrations and migrate")
    for cmd in ["makemigrations", "migrate"]:
        py_man_cmd = f"python manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def make_groups_and_users():
    print("Create groups and users")
    for cmd in ["plom_create_groups", "plom_create_demo_users"]:
        py_man_cmd = f"python manage.py {cmd}"
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
        "plom_preparation_classlist upload useful_files_for_testing/cl_good.csv",
        "plom_preparation_qvmap generate",
    ]:
        py_man_cmd = f"python manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def launch_huey_workers():
    print("Launching huey workers for background tasks")
    for cmd in ["djangohuey"]:
        py_man_cmd = f"python manage.py {cmd}"
        return subprocess.Popen(split(py_man_cmd))


def launch_server():
    print("Launching django server")
    for cmd in ["runserver 8000"]:
        py_man_cmd = f"python manage.py {cmd}"
        return subprocess.Popen(split(py_man_cmd))


def build_db_via_huey():
    print("Populating database in background")
    for cmd in ["plom_papers build_db"]:
        py_man_cmd = f"python manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))


def wait_for_db_to_be_ready():
    py_man_cmd = "python manage.py plom_papers status"
    while True:
        output = subprocess.check_output(split(py_man_cmd)).decode("utf-8")
        if "Database is ready" in output:
            print("Database is ready - continuing to the next step of the demo.")
            break
        else:
            print("Still waiting for database to be populated. Sleeping 2 seconds.")
            sleep(2)


def build_papers_via_huey():
    print("Build extra-page and test-paper pdfs in background via huey")
    for cmd in ["plom_preparation_extrapage --build", "plom_build_papers --start-all"]:
        py_man_cmd = f"python manage.py {cmd}"
        subprocess.Popen(split(py_man_cmd))


def wait_for_papers_to_be_ready():
    py_man_ep = "python manage.py plom_preparation_extrapage"
    py_man_papers = "python manage.py plom_build_papers --status"
    ep_todo = True
    papers_todo = False
    while True:
        if ep_todo:
            out_ep = subprocess.check_output(split(py_man_ep)).decode("utf-8")
            if "complete" in out_ep:
                print("Extra page is built.")
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


def wait_for_exit():
    while True:
        i = input("Press Enter to quit:")
        if not i:
            break


def clean_up_processes(procs):
    print("Terminating background processes")
    for proc in procs:
        proc.terminate()


def main():
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
    huey_worker_proc = launch_huey_workers()
    print("*" * 40)
    build_db_via_huey()
    print("*" * 40)
    server_proc = launch_server()
    print("v" * 40)
    print("Everything is now up and running")
    print("^" * 40)

    wait_for_db_to_be_ready()

    print("*" * 40)
    build_papers_via_huey()
    print("*" * 40)

    wait_for_papers_to_be_ready()

    print("*" * 40)
    wait_for_exit()
    print("*" * 40)
    clean_up_processes([huey_worker_proc, server_proc])
    print("*" * 40)


if __name__ == "__main__":
    main()
