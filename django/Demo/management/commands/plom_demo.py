# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

import os
import subprocess
from time import sleep
from shlex import split

from django.core.management.base import BaseCommand, CommandError

from Demo.services import (
    DemoProcessesService,
    DemoCreationService,
    DemoBundleService,
    DemoHWBundleService,
)


class Command(BaseCommand):
    help = "WebPlom demo. For testing, debugging and development."

    def papers_and_db(self, dcs: DemoCreationService):
        print("*" * 40)
        dcs.build_db_and_papers()
        dcs.wait_for_papers_to_be_ready()

        print("*" * 40)
        dcs.download_zip()

    def create_bundles(
        self,
        dbs: DemoBundleService,
        dhs: DemoHWBundleService,
        number_of_bundles,
        homework_bundles,
    ):
        dbs.scribble_on_exams(
            number_of_bundles=number_of_bundles,
            extra_page_papers=[
                31,
                32,
                33,
                49,
                50,
            ],  # The first three papers in fake_bundle4 have extra pages.
            garbage_page_papers=[1, 2],
            duplicate_pages={1: 3, 2: 6},
            duplicate_qr=[3, 4],
            wrong_version=[5, 6],
        )

        for paper_number, question_list in homework_bundles.items():
            dhs.make_hw_bundle(paper_number, question_list=question_list)

    def upload_bundles(
        self, dcs: DemoCreationService, number_of_bundles, homework_bundles
    ):
        print("*" * 40)
        dcs.upload_bundles(
            number_of_bundles=number_of_bundles, homework_bundles=homework_bundles
        )

        dcs.wait_for_upload(
            number_of_bundles=number_of_bundles,
        )

    def read_bundles(
        self,
        dcs: DemoCreationService,
        dhs: DemoHWBundleService,
        number_of_bundles,
        homework_bundles,
    ):
        print("*" * 40)
        dcs.read_qr_codes(
            number_of_bundles=number_of_bundles,
        )
        dhs.map_homework_pages(homework_bundles=homework_bundles)

        print("*" * 40)
        dcs.wait_for_qr_read(
            number_of_bundles=number_of_bundles,
        )

        dcs.map_extra_pages_to_bundle4()

    def push_bundles(
        self, dcs: DemoCreationService, number_of_bundles, homework_bundles
    ):
        print("*" * 40)
        dcs.push_if_ready(
            number_of_bundles=number_of_bundles, homework_bundles=homework_bundles
        )

    def post_server_init(self, dcs: DemoCreationService, stop_at: str):
        self.papers_and_db(dcs)

        print("*" * 40)
        number_of_bundles = 5

        homework_bundles = {
            61: [[1], [2], [], [2, 3], [3]],
            62: [[1], [1, 2], [2], [], [3]],
            63: [[1, 2], [3], []],
        }
        bundle_service = DemoBundleService()
        homework_service = DemoHWBundleService()
        self.create_bundles(
            bundle_service, homework_service, number_of_bundles, homework_bundles
        )

        self.upload_bundles(dcs, number_of_bundles, homework_bundles)
        if stop_at == "bundles_uploaded":
            return

        self.read_bundles(dcs, homework_service, number_of_bundles, homework_bundles)
        if stop_at == "bundles_read":
            return

        self.push_bundles(dcs, number_of_bundles, homework_bundles)
        if stop_at == "bundles_pushed":
            return

        print("*" * 40)
        dcs.create_rubrics()

    def run_randomarker(self):
        # TODO: hardcoded port numbers!
        cmd = "python3 -m plom.client.randoMarker -s localhost:8000 -u demoMarker1 -w demoMarker1"
        print(f"RandoMarking!  calling: {cmd}")
        subprocess.check_call(split(cmd), env=dict(os.environ, WEBPLOM="1"))
        cmd = "python3 -m plom.client.randoIDer -s localhost:8000 -u demoMarker1 -w demoMarker1"
        print(f"RandoIDing!  calling: {cmd}")
        subprocess.check_call(split(cmd), env=dict(os.environ, WEBPLOM="1"))

    def wait_for_exit(self):
        while True:
            x = input("Type 'quit' and press Enter to exit the demo: ")
            if x.casefold() == "quit":
                break

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-waiting",
            action="store_true",
            help="Do not wait for user input at the end of the demo sequence before stopping the demo.",
        )
        parser.add_argument(
            "--stop-at",
            action="store",
            choices=[
                "migrations",
                "users",
                "preparation",
                "bundles-uploaded",
                "bundles-read",
                "bundles-pushed",
            ],
            nargs=1,
            help="Stop the demo sequence at a certain breakpoint.",
        )
        parser.add_argument(
            "--randomarker",
            action="store_true",
            help="Run the plom-client randomarker.",
        )

    def handle(self, *args, **options):
        stop_at = options["stop_at"]
        if stop_at is not None:
            stop_at = stop_at[0]
            if options["randomarker"]:
                raise CommandError(
                    "Cannot run plom-client randomarker with a demo breakpoint."
                )

        proc_service = DemoProcessesService()
        proc_service.initialize_server_and_db()

        if stop_at == "migrate":
            return

        print("*" * 40)
        huey_worker_proc = proc_service.launch_huey_workers()

        creation_service = DemoCreationService()
        print("*" * 40)
        creation_service.make_groups_and_users()

        if stop_at == "users":
            huey_worker_proc.terminate()
            return

        # TODO: I get errors if I move this after launching the server...
        print("*" * 40)
        creation_service.prepare_assessment()

        if stop_at == "preparation":
            huey_worker_proc.terminate()
            return

        print("*" * 40)
        server_proc = proc_service.launch_server()

        try:  # We're guaranteed to hit the cleanup code in the "finally" block
            self.post_server_init(creation_service, stop_at)

            if options["randomarker"]:
                self.run_randomarker()

            if not options["no_waiting"]:
                sleep(2)
                print("*" * 72)
                self.wait_for_exit()
            sleep(0.1)
            print("v" * 40)
        finally:
            huey_worker_proc.terminate()
            server_proc.terminate()
