# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom.misc_utils import format_int_list_with_runs
from plom.version_maps import version_map_from_file
from plom.plom_exceptions import PlomDependencyConflict

from Papers.services import SpecificationService, PaperInfoService, PaperCreatorService
from ...services import PQVMappingService, PapersPrinted


class Command(BaseCommand):
    help = "Displays the current status of the question-version map and allows user generate/upload/download/remove it."

    def show_status(self) -> None:
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("There is no valid test specification. Stopping.")

        if PaperInfoService().is_paper_database_populated():
            paper_list = PaperInfoService().which_papers_in_database()
            self.stdout.write(
                "There is a question-version mapping on the server "
                f"with {len(paper_list)} rows: "
                f"papers {format_int_list_with_runs(paper_list, zero_padding=4)}"
            )
            if PapersPrinted.have_papers_been_printed():
                print("Papers have been printed: cannot change qvmap.")

        else:
            self.stdout.write(
                "There is no question-version mapping, nor papers in the database."
            )
            self.stdout.write(
                f"Recommended minimum number of papers to produce is {PQVMappingService().get_minimum_number_to_produce()}"
            )

    def generate_pqv_map(
        self, *, number_to_produce: int | None = None, first: int | None = None
    ) -> None:
        if PapersPrinted.have_papers_been_printed():
            raise CommandError("Paper have been printed. You cannot change qvmap.")

        if not SpecificationService.is_there_a_spec():
            raise CommandError("There no valid test specification.")

        if PaperInfoService().is_paper_database_populated():
            self.stderr.write("Test-papers already saved to database - stopping.")
            return

        min_production = PQVMappingService().get_minimum_number_to_produce()

        if number_to_produce is None:
            number_to_produce = min_production
            self.stdout.write(
                f"Number-to-produce not supplied, using recommended number = {number_to_produce}."
            )
        elif number_to_produce < min_production:
            self.stdout.write(
                f"Warning: Supplied number-to-produce={number_to_produce} is less than the recommended minimum={min_production}."
            )

        if first is None:
            first = 1

        qv_map = PQVMappingService().make_version_map(number_to_produce, first=first)
        try:
            PaperCreatorService().add_all_papers_in_qv_map(qv_map, background=False)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write(
            f"Database populated with {len(qv_map)} test-papers, starting from {first}."
        )

    def download_pqv_map(self) -> None:
        if not PaperInfoService().is_paper_database_fully_populated():
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
        PQVMappingService().pqv_map_to_csv(save_path)
        self.stdout.write(f"Wrote {save_path}")

    def upload_pqv_map(self, f: Path) -> None:
        if PapersPrinted.have_papers_been_printed():
            raise CommandError("Paper have been printed. You cannot change qvmap.")

        if PaperInfoService().is_paper_database_populated():
            self.stderr.write("Test-papers already saved to database - stopping.")
            return

        self.stdout.write(f"Reading qvmap from {f}")
        try:
            vm = version_map_from_file(f)
        except ValueError as e:
            raise CommandError(e)

        try:
            PaperCreatorService().add_all_papers_in_qv_map(vm, background=False)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write(f"Uploaded qvmap from {f}")

    def remove_pqv_map(self) -> None:
        if PapersPrinted.have_papers_been_printed():
            raise CommandError("Paper have been printed. You cannot change qvmap.")

        if PaperInfoService().how_many_papers_in_database() == 0:
            self.stderr.write("No test-papers in the database - stopping.")
            return

        try:
            PaperCreatorService().remove_all_papers_from_db(background=False)
        except PlomDependencyConflict as e:
            raise CommandError(e) from e
        self.stdout.write("Question-version map and papers removed from server.")

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

    def handle(self, *args, **options) -> None:
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
