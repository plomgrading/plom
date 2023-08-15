# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov

import subprocess
from time import sleep
from shlex import split
import sys
from dataclasses import asdict

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from django.core.management import call_command
from django.conf import settings

from Scan.models import ExtraStagingImage
from Papers.services import SpecificationService
from Preparation import useful_files_for_testing as useful_files

from .config_files import PlomServerConfig


class DemoCreationService:
    """Handle creating the demo exam and populating the database."""

    def make_groups_and_users(self):
        print("Create groups and users")
        call_command("plom_create_groups")
        call_command("plom_create_demo_users")

    def prepare_assessment(self, config: PlomServerConfig):
        print("Prepare assessment: ")
        print(
            "\tUpload demo spec, upload source pdfs and classlist, enable prenaming, and generate qv-map"
        )
        spec_path = config.test_spec
        if spec_path == "demo":
            call_command("plom_demo_spec")
        else:
            call_command(
                "plom_preparation_test_spec",
                "upload",
                f"{spec_path}",
            )

        fixdir = settings.FIXTURE_DIRS[0]
        fixdir.mkdir(exist_ok=True)
        call_command(
            "dumpdata",
            "--natural-foreign",
            "Papers.Specification",
            f"-o{fixdir}/test_spec.json",
        )

        if config.test_sources:
            sources = config.test_sources
            for i, src in enumerate(sources):
                if src == "demo":
                    src = resources.files(useful_files) / f"test_version{i+1}.pdf"
                call_command(
                    "plom_preparation_test_source",
                    "upload",
                    f"-v {i+1}",
                    src,
                )
        else:
            print("No test sources specified. Stopping.")
            return

        if config.prenaming_enabled:
            call_command("plom_preparation_prenaming", enable=True)

        if config.classlist:
            f = config.classlist
            if f == "demo":
                f = resources.files(useful_files) / "cl_for_demo.csv"
            call_command(
                "plom_preparation_classlist",
                "upload",
                f,
            )

        if (
            config.num_to_produce is not None
        ):  # TODO: users should be able to specify path to custom qvmap
            n_to_produce = config.num_to_produce
            call_command("plom_preparation_qvmap", "generate", f"-n {n_to_produce}")
        else:
            print("No papers to produce. Stopping.")
            return

        call_command(
            "dumpdata",
            "--natural-foreign",
            "Preparation",
            f"-o{fixdir}/preparation.json",
        )

    def build_db_and_papers(self):
        print("Populating database in background")
        call_command("plom_papers", "build_db", "manager")

        fixdir = settings.FIXTURE_DIRS[0]
        fixdir.mkdir(exist_ok=True)
        call_command(
            "dumpdata",
            "--natural-foreign",
            "Papers.Paper",
            "--exclude=Papers.FixedPage",
            "--exclude=Papers.IDPage",
            f"-o{fixdir}/papers.json",
        )

        call_command("plom_preparation_extrapage", "build")
        call_command("plom_preparation_scrap_paper", "build")
        call_command("plom_build_papers", "--start-all")

    def wait_for_papers_to_be_ready(self):
        py_man_ep = "python3 manage.py plom_preparation_extrapage"
        py_man_sp = "python3 manage.py plom_preparation_scrap_paper"
        py_man_papers = "python3 manage.py plom_build_papers --status"

        ep_todo = True
        sp_todo = True
        papers_todo = True

        sleep(1)
        while True:
            if ep_todo:
                out_ep = subprocess.check_output(split(py_man_ep)).decode("utf-8")
                if "complete" in out_ep:
                    print("Extra page is built")

                    ep_todo = False
            if sp_todo:
                out_sp = subprocess.check_output(split(py_man_sp)).decode("utf-8")
                if "complete" in out_sp:
                    print("Scrap paper is built")

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
                call_command("plom_preparation_status", set=["finished"])
                print("Test preparation marked as finished.")
                print(
                    "Extra page, Scrap paper, and papers all built - continuing to next step of demo."
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
        for bundle in homework_bundles:
            paper_number = bundle["paper_number"]
            bundle_name = f"fake_hw_bundle_{paper_number}.pdf"
            cmd = f"plom_staging_bundles upload demoScanner{1} {bundle_name}"
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

    def push_if_ready(self, number_of_bundles=3, homework_bundles=[], attempts=15):
        print(
            "Try to push all bundles - some will fail since they are not yet ready, or contain unknowns/errors etc"
        )
        todo = [f"fake_bundle{k+1}" for k in range(number_of_bundles)]
        for bundles in homework_bundles:
            paper_number = bundles["paper_number"]
            todo.append(f"fake_hw_bundle_{paper_number}")

        while True:
            done = []
            for bundle in todo:
                cmd = f"plom_staging_bundles status {bundle}"
                py_man_cmd = f"python3 manage.py {cmd}"
                out_stat = subprocess.check_output(
                    split(py_man_cmd), stderr=subprocess.STDOUT
                ).decode("utf-8")
                if "perfect" in out_stat:
                    push_cmd = f"python3 manage.py plom_staging_bundles push {bundle} demoScanner1"
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
        call_command("plom_rubrics", "init", "manager")
        call_command("plom_rubrics", "push", "--demo", "manager")

    def map_extra_pages(self, config: PlomServerConfig):
        """Map extra pages that are in otherwise fully fixed-page bundles."""
        if config.bundles is None:
            return

        bundles = config.bundles
        for i, bundle in enumerate(bundles):
            bundle_dict = asdict(bundle)
            bundle_slug = f"fake_bundle{i+1}"
            if "extra_page_papers" in bundle_dict.keys():
                extra_page_papers = bundle_dict["extra_page_papers"]
                extra_pages = ExtraStagingImage.objects.filter(
                    staging_image__bundle__slug=bundle_slug,
                ).order_by("staging_image__bundle_order")

                n_questions = SpecificationService.get_n_questions()

                for i, ex_paper in enumerate(extra_page_papers):
                    paper_extra_pages = extra_pages[i * 2 : i * 2 + 2]

                    # command must be called twice, since the demo generates double extra pages
                    for page in paper_extra_pages:
                        call_command(
                            "plom_staging_assign_extra",
                            "assign",
                            "demoScanner1",
                            bundle_slug,
                            "-i",
                            page.staging_image.bundle_order,
                            "-t",
                            ex_paper,
                            "-q",
                            n_questions,  # default to last question
                        )

    def map_pages_to_discards(self, config: PlomServerConfig):
        if config.bundles is None:
            return

        bundles = config.bundles
        for i, bundle in enumerate(bundles):
            bundle_slug = f"fake_bundle{i+1}"
            if "discard_pages" in asdict(bundle).keys():
                for page in bundle.discard_pages:
                    call_command(
                        "plom_staging_discard", "demoScanner1", bundle_slug, page
                    )
