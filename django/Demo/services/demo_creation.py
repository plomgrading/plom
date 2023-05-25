# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

import subprocess
from time import sleep
from shlex import split

from django.core.management import call_command
from django.conf import settings


class DemoCreationService:
    """Handle creating the demo exam and populating the database."""

    def make_groups_and_users(self):
        print("Create groups and users")
        call_command("plom_create_groups")
        call_command("plom_create_demo_users")

    def prepare_assessment(self):
        print("Prepare assessment: ")
        print(
            "\tUpload demo spec, upload source pdfs and classlist, enable prenaming, and generate qv-map"
        )
        call_command("plom_demo_spec")

        (settings.BASE_DIR / "fixtures").mkdir(exist_ok=True)
        call_command(
            "dumpdata",
            "--natural-foreign",
            "Papers.Specification",
            f"-o{settings.BASE_DIR}/fixtures/test_spec.json",
        )

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

        call_command(
            "dumpdata",
            "--natural-foreign",
            "Preparation",
            f"-o{settings.BASE_DIR}/fixtures/preparation.json",
        )

    def build_db_and_papers(self):
        print("Populating database in background")
        call_command("plom_papers", "build_db")

        call_command(
            "dumpdata",
            "--natural-foreign",
            "Papers.Paper",
            "--exclude=Papers.FixedPage",
            "--exclude=Papers.IDPage",
            f"-o{settings.BASE_DIR}/fixtures/papers.json",
        )

        call_command("plom_preparation_extrapage", "build")
        call_command("plom_build_papers", "--start-all")

    def wait_for_papers_to_be_ready(self):
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
                out_papers = subprocess.check_output(split(py_man_papers)).decode(
                    "utf-8"
                )
                if "All papers are now built" in out_papers:
                    print("Papers are now built.")
                    papers_todo = False
            if papers_todo or ep_todo:
                print("Still waiting for pdf production tasks. Sleeping.")
                sleep(1)
            else:
                print(
                    "Extra page and papers all built - continuing to next step of demo."
                )
                break

    def download_zip(self):
        print("Download a zip of all the papers")
        cmd = "plom_build_papers --download-all"
        py_man_cmd = f"python3 manage.py {cmd}"
        subprocess.check_call(split(py_man_cmd))

    def upload_bundles(self, number_of_bundles=3, homework_bundles={}):
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

    def wait_for_upload(self, number_of_bundles=3, homework_bundles={}):
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

    def read_qr_codes(self, number_of_bundles=3):
        for n in range(1, number_of_bundles + 1):
            cmd = f"plom_staging_bundles read_qr fake_bundle{n}"
            py_man_cmd = f"python3 manage.py {cmd}"
            subprocess.check_call(split(py_man_cmd))
            sleep(0.5)

    def wait_for_qr_read(self, number_of_bundles=3):
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

    def push_if_ready(self, number_of_bundles=3, homework_bundles={}, attempts=15):
        print(
            "Try to push all bundles - some will fail since they are not yet ready, or contain unknowns/errors etc"
        )
        todo = [f"fake_bundle{k+1}" for k in range(number_of_bundles)]
        for n in homework_bundles:
            todo.append(f"fake_hw_bundle_{n}")

        while True:
            done = []
            for bundle in todo:
                cmd = f"plom_staging_bundles status {bundle}"
                py_man_cmd = f"python3 manage.py {cmd}"
                out_stat = subprocess.check_output(
                    split(py_man_cmd), stderr=subprocess.STDOUT
                ).decode("utf-8")
                if "perfect" in out_stat:
                    push_cmd = f"python3 manage.py plom_staging_bundles push {bundle}"
                    subprocess.check_call(split(push_cmd))
                    done.append(bundle)
                    sleep(1)
                elif "cannot push" in out_stat:
                    print(
                        f"Cannot push {bundle} because it contains unknowns or errors"
                    )
                    done.append(bundle)

            for bundle in done:
                todo.remove(bundle)
            if len(todo) > 0 and attempts > 0:
                print(
                    f"Still waiting for bundles {todo} to process - sleep between attempts"
                )
                attempts -= 1
                sleep(1)
            else:
                print("All bundles pushed.")
                break

    def create_rubrics(self):
        call_command("plom_rubrics", "init")
        call_command("plom_rubrics", "push", "--demo")

    def map_extra_pages_to_bundle4(self):
        """
        Map the extra pages generated in fake_bundle4.

        TODO: This function is very hardcoded.
        """

        extra_pages = {31: [2, 3], 32: [10, 11], 33: [18, 19]}

        for paper_number, pages in extra_pages.items():
            print(f"Assigning extra pages to test {paper_number} in fake bundle 4")
            for question, page in enumerate(pages):
                call_command(
                    "plom_staging_assign_extra",
                    "assign",
                    "demoScanner1",
                    "fake_bundle4",
                    "-i",
                    page,
                    "-t",
                    paper_number,
                    "-q",
                    question + 1,
                )
