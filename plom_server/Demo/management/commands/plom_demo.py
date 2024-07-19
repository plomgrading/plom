# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

import subprocess
from time import sleep
from shlex import split
import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from Launcher.services import LaunchProcessesService
from ...services import (
    DemoCreationService,
    DemoBundleService,
    DemoHWBundleService,
    ConfigFileService,
)
from Demo import config_files as demo_config_files
from Identify.services import IDDirectService


class Command(BaseCommand):
    help = """
        WebPlom demo. For testing, debugging and development.

        Some aspects of the server can be changed via command line
        arguments.  Others via environment variables, including
        ``PLOM_DATABASE_BACKEND``, ``PLOM_DATABASE_NAME``,
        ``PLOM_DATABASE_USER``, ``PLOM_DATABASE_PASSWORD``, and other
        ``PLOM_*`` variables.
    """

    def build_papers(self, dcs: DemoCreationService):
        print("*" * 40)
        dcs.build_papers()
        dcs.wait_for_papers_to_be_ready()

        print("*" * 40)
        dcs.download_zip()

    def create_bundles(
        self,
        dbs: DemoBundleService,
        dhs: DemoHWBundleService,
        config,
        homework_bundles,
    ) -> None:
        if config.bundles:
            dbs.scribble_on_exams(config)

        for bundle in homework_bundles:
            dhs.make_hw_bundle(bundle)

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
        config,
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

        dcs.map_extra_pages(config)
        dcs.map_pages_to_discards(config)

    def push_bundles(
        self, dcs: DemoCreationService, number_of_bundles, homework_bundles
    ):
        print("*" * 40)
        dcs.push_if_ready(
            number_of_bundles=number_of_bundles, homework_bundles=homework_bundles
        )

    def direct_id_hw_bundles(self, homework_bundles):
        for hw_bundle in homework_bundles:
            if "student_id" in hw_bundle and "student_name" in hw_bundle:
                print(
                    f"Direct ID of homework paper {hw_bundle['paper_number']} as student {hw_bundle['student_id']} {hw_bundle['student_name']}"
                )
                # use the _cmd here so that it looks up the username for us.
                IDDirectService().identify_direct_cmd(
                    "demoManager1",
                    hw_bundle["paper_number"],
                    hw_bundle["student_id"],
                    hw_bundle["student_name"],
                )

    def post_server_init(self, dcs: DemoCreationService, config, stop_at: str):
        self.build_papers(dcs)

        print("*" * 40)
        if config.bundles:
            number_of_bundles = len(config.bundles)
            bundle_service = DemoBundleService()
        else:
            bundle_service = None
            number_of_bundles = 0

        if config.hw_bundles:
            homework_bundles = config.hw_bundles
            homework_service = DemoHWBundleService()
        else:
            homework_bundles = []
            homework_service = None

        if bundle_service is None and homework_service is None:
            print("No bundles detected - stopping.")
            return

        assert bundle_service is not None
        assert homework_service is not None

        self.create_bundles(bundle_service, homework_service, config, homework_bundles)

        if stop_at == "bundles-created":
            return

        self.upload_bundles(dcs, number_of_bundles, homework_bundles)
        if stop_at == "bundles-uploaded":
            return

        self.read_bundles(
            dcs, homework_service, config, number_of_bundles, homework_bundles
        )
        if stop_at == "bundles-read":
            return

        self.push_bundles(dcs, number_of_bundles, homework_bundles)
        self.direct_id_hw_bundles(homework_bundles)  # Direct-ID any homework bundles
        if stop_at == "bundles-pushed":
            return

        print("*" * 40)
        dcs.create_rubrics()

    def run_randomarker(self, *, port):
        # TODO: hardcoded http://
        srv = f"http://localhost:{port}"

        # rando-id and then rando-mark
        cmd = f"python3 -m plom.client.randoIDer -s {srv} -u demoMarker1 -w demoMarker1"
        print(f"RandoIDing!  calling: {cmd}")
        subprocess.check_call(split(cmd))

        cmds = (
            f"python3 -m plom.client.randoMarker -s {srv} -u demoMarker1 -w demoMarker1 --partial 25",
            f"python3 -m plom.client.randoMarker -s {srv} -u demoMarker2 -w demoMarker2 --partial 33",
            f"python3 -m plom.client.randoMarker -s {srv} -u demoMarker3 -w demoMarker3 --partial 50",
        )
        for cmd in cmds:
            print(f"RandoMarking!  calling: {cmd}")
            subprocess.check_call(split(cmd))

    def upload_solutions(self):
        from Finish import useful_files_for_testing as useful_files

        print("*" * 40)
        print(" Uploading solutions spec and source pdfs")

        soln_spec_path = resources.files(useful_files) / "soln_specification.toml"
        call_command("plom_soln_spec", "upload", soln_spec_path)
        for v in [1, 2]:
            soln_pdf_path = resources.files(useful_files) / f"solutions{v}.pdf"
            call_command("plom_soln_sources", "upload", "-v", v, soln_pdf_path)

    def wait_for_exit(self):
        while True:
            x = input("Type 'quit' and press Enter to exit the demo: ")
            if x.casefold() == "quit":
                break

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            action="store",
            nargs=1,
            help="Use a TOML config file for creating the demo exam structure.",
        )
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
                "bundles-created",
                "bundles-uploaded",
                "bundles-read",
                "bundles-pushed",
            ],
            nargs=1,
            help="Stop the demo sequence at a certain breakpoint.",
        )
        parser.add_argument(
            "--port",
            action="store",
            type=int,
            default=8000,
            help="What port number to run on, default 8000.",
        )
        parser.add_argument(
            "--randomarker",
            action="store_true",
            help="Run the plom-client randomarker.",
        )
        parser.add_argument(
            "--solutions",
            action="store_true",
            help="Build demo solutions.",
        )
        parser.add_argument(
            "--quick",
            action="store_true",
            help="Run a quicker demo with fewer papers and bundles.",
        )
        parser.add_argument(
            "--long",
            action="store_true",
            help="Run a longer demo with more papers and bundles.",
        )

    def handle(self, *args, **options):
        stop_at = options["stop_at"]

        if stop_at is not None:
            stop_at = stop_at[0]
            self.stdout.write(f"Note that demo script will stop after '{stop_at}'")

            if options["randomarker"]:
                raise CommandError(
                    "Cannot run plom-client randomarker with a demo breakpoint."
                )

        if options["quick"] and options["long"]:
            self.stderr.write("Cannot run a short demo at the same time")
            return

        config_path = options["config"]
        if config_path is None:
            if options["quick"]:
                config = ConfigFileService.read_server_config(
                    resources.files(demo_config_files) / "quick_demo_config.toml"
                )
            elif options["long"]:
                config = ConfigFileService.read_server_config(
                    resources.files(demo_config_files) / "long_demo_config.toml"
                )
            else:
                config = ConfigFileService.read_server_config(
                    resources.files(demo_config_files) / "full_demo_config.toml"
                )
        else:
            try:
                config = ConfigFileService.read_server_config(config_path[0])
            except Exception as e:
                raise CommandError(e)
        print(config)

        proc_service = LaunchProcessesService()
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
        creation_service.prepare_assessment(config)

        if options["solutions"]:
            self.upload_solutions()

        print("*" * 40)
        server_proc = proc_service.launch_server(port=options["port"])

        try:  # We're guaranteed to hit the cleanup code in the "finally" block
            if stop_at == "preparation" or not config.num_to_produce:
                pass
            else:
                self.post_server_init(creation_service, config, stop_at)

                if options["randomarker"]:
                    self.run_randomarker(port=options["port"])

            if not options["no_waiting"]:
                sleep(2)
                print("*" * 72)
                self.wait_for_exit()

            sleep(0.1)
            print("v" * 40)
        finally:
            huey_worker_proc.terminate()
            server_proc.terminate()
