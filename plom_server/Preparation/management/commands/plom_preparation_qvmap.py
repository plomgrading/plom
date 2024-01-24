# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom.misc_utils import format_int_list_with_runs
from plom.version_maps import version_map_from_file
from Papers.services import SpecificationService

from ...services import PQVMappingService, TestPreparedSetting


class Command(BaseCommand):
    help = "Displays the current status of the question-version map and allows user generate/download/remove it."

    def show_status(self):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("There is no valid test specification. Stopping.")

        pqvms = PQVMappingService()
        if pqvms.is_there_a_pqv_map():
            paper_list = pqvms.list_of_paper_numbers()
            self.stdout.write(
                f"There is a question-version mapping on the server with {len(paper_list)} rows = {format_int_list_with_runs(paper_list)}"
            )
            if TestPreparedSetting.is_test_prepared():
                print("Exam preparation is locked: cannot change qvmap.")

        else:
            self.stdout.write("There is no question-version mapping.")
            self.stdout.write(
                f"Recommended minimum number of papers to produce is {pqvms.get_minimum_number_to_produce()}"
            )

    def generate_pqv_map(
        self, *, number_to_produce: int | None = None, first: int | None = None
    ) -> None:
        if TestPreparedSetting.is_test_prepared():
            raise CommandError("Test is marked as prepared. You cannot change qvmap.")

        if not SpecificationService.is_there_a_spec():
            raise CommandError("There no valid test specification.")
        pqvms = PQVMappingService()
        if pqvms.is_there_a_pqv_map():
            raise CommandError(
                "There is already a question-version mapping on the server."
            )
        min_production = pqvms.get_minimum_number_to_produce()

        if number_to_produce is None:
            number_to_produce = min_production
            self.stdout.write(
                f"Number-to-produce not supplied, using recommended number = {number_to_produce}."
            )
        elif number_to_produce < pqvms.get_minimum_number_to_produce():
            self.stdout.write(
                f"Warning: Supplied number-to-produce={number_to_produce} is less than the recommended minimum={min_production}."
            )

        if first is None:
            first = 1

        pqvms.generate_and_set_pqvmap(number_to_produce, first=first)
        self.stdout.write(
            f"Question-version map generated: {number_to_produce} rows starting from {first}."
        )

    def download_pqv_map(self):
        pqvms = PQVMappingService()
        if not pqvms.is_there_a_pqv_map():
            raise CommandError(
                "There is no a question-version mapping on the server. Stopping"
            )

        save_path = Path("question_version_map.csv")
        if save_path.exists():
            s = f"A file exists at {save_path} - overwrite it? [y/N] "
            choice = input(s).lower()
            if choice != "y":
                self.stdout.write("Skipping.")
                return
            else:
                self.stdout.write(f"Overwriting {save_path}.")
        pqvms.pqv_map_to_csv(save_path)
        self.stdout.write(f"Wrote {save_path}")

    def upload_pqv_map(self, f: Path) -> None:
        if TestPreparedSetting.is_test_prepared():
            raise CommandError("Test is marked as prepared. You cannot change qvmap.")

        pqvms = PQVMappingService()
        if pqvms.is_there_a_pqv_map():
            raise CommandError("Already has a question-version map - remove it first")

        self.stdout.write(f"Reading qvmap from {f}")
        try:
            vm = version_map_from_file(f)
        except ValueError as e:
            raise CommandError(e)

        try:
            pqvms.use_pqv_map(vm)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write(f"Uploaded qvmap from {f}")

    def remove_pqv_map(self):
        if TestPreparedSetting.is_test_prepared():
            raise CommandError("Exam preparation is locked: cannot change qvmap.")

        pqvms = PQVMappingService()
        if not pqvms.is_there_a_pqv_map():
            self.stderr.write(
                "There is no a question-version mapping on the server. Stopping"
            )
            return
        pqvms.remove_pqv_map()
        self.stdout.write("Question-version map removed from server.")

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to generating/downloading/deleting the question-version map.",
        )
        sub.add_parser("status", help="Show details of the question-version map")
        p = sub.add_parser("generate", help="Generate the question-version map")
        p.add_argument(
            "-n",
            "--number-to-produce",
            metavar="N",
            type=int,
            help="""
                The number of papers to produce.  If not present, the system will
                compute this for you (not recommended).
            """,
        )
        p.add_argument(
            "--first-paper",
            metavar="F",
            type=int,
            help="""
                The paper number to start at.  Defaults to 1 if omitted.
            """,
        )
        sub.add_parser("download", help="Download the question-version map")
        p = sub.add_parser("upload", help="Upload a question-version map")
        p.add_argument("csv_or_json_file")
        sub.add_parser("remove", help="Remove the question-version map")

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "generate":
            self.generate_pqv_map(
                number_to_produce=options["number_to_produce"],
                first=options["first_paper"],
            )

        elif options["command"] == "download":
            self.download_pqv_map()
        elif options["command"] == "upload":
            self.upload_pqv_map(options["csv_or_json_file"])
        elif options["command"] == "remove":
            self.remove_pqv_map()
        else:
            self.print_help("manage.py", "plom_preparation_qvmap")
