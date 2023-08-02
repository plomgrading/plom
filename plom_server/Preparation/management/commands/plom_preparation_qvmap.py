# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2023 Edith Coates

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom.misc_utils import format_int_list_with_runs
from Papers.services import SpecificationService
from SpecCreator.services import StagingSpecificationService

from ...services import PQVMappingService


class Command(BaseCommand):
    help = "Displays the current status of the question-version map and allows user generate/download/remove it."

    def show_status(self):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("There no valid test specification. Stopping.")

        pqvms = PQVMappingService()
        if pqvms.is_there_a_pqv_map():
            paper_list = pqvms.list_of_paper_numbers()
            self.stdout.write(
                f"There is a question-version mapping on the server with {len(paper_list)} rows = {format_int_list_with_runs(paper_list)}"
            )
        else:
            self.stdout.write("There no is a question-version mapping.")
            self.stdout.write(
                f"Recommended minimum number of papers to produce is {pqvms.get_minimum_number_to_produce()}"
            )

    def generate_pqv_map(self, number_to_produce=None):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("There no valid test specification. Stopping.")
            return
        pqvms = PQVMappingService()
        if pqvms.is_there_a_pqv_map():
            self.stderr.write(
                "There is already a question-version mapping on the server. Stopping"
            )
            return
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

        self.stdout.write(
            f"Question-version map with {number_to_produce} rows generated."
        )
        pqvms.generate_and_set_pqvmap(number_to_produce)

    def download_pqv_map(self):
        pqvms = PQVMappingService()
        if not pqvms.is_there_a_pqv_map():
            self.stderr.write(
                "There is no a question-version mapping on the server. Stopping"
            )
            return

        save_path = Path(f"question_version_map.csv")
        if save_path.exists():
            self.stdout.write(f"A file exists at {save_path} - overwrite it? [y/N]")
            choice = input().lower()
            if choice != "y":
                self.stdout.write(f"Skipping.")
                return
            else:
                self.stdout.write(f"Overwriting {save_path}.")
        csv_text = pqvms.get_pqv_map_as_csv()
        with open(save_path, "w") as fh:
            fh.write(csv_text)

    def remove_pqv_map(self):
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
        sp_S = sub.add_parser("status", help="Show details of the question-version map")
        sp_G = sub.add_parser("generate", help="Generate the question-version map")
        sp_D = sub.add_parser("download", help="Download the question-version map")
        sp_R = sub.add_parser("remove", help="Remove the question-version map")

        sp_G.add_argument(
            "-n",
            "--number_to_produce",
            type=int,
            help="The number of papers to produce. If not present, then system will compute this for you (not recommended).",
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "generate":
            self.generate_pqv_map(number_to_produce=options["number_to_produce"])

        elif options["command"] == "download":
            self.download_pqv_map()
        elif options["command"] == "remove":
            self.remove_pqv_map()
        else:
            self.print_help("manage.py", "plom_preparation_qvmap")
