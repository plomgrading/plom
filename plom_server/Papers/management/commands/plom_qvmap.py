# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError

from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError
from plom.version_maps import version_map_from_file
from plom_server.Preparation.services import PQVMappingService
from ...services import PaperCreatorService, PaperInfoService


class Command(BaseCommand):
    help = "Display the current state of test-papers in the database, populate the test-paper database, or clear."

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command", description="Display, populate, or clear test-papers."
        )
        sp.add_parser(
            "status", help="Show the current state of test-papers in the database."
        )

        b = sp.add_parser(
            "build_db",
            help="""
                Populate the database with test-papers - uses a default
                version map.
            """,
        )
        b.add_argument(
            "-n",
            "--number-to-produce",
            metavar="N",
            type=int,
            help="""
                The number of papers to produce.  If not present, the system will
                compute this for you (not recommended).
            """,
        )
        b.add_argument(
            "--first-paper",
            metavar="F",
            type=int,
            help="""
                The paper number to start at.  Defaults to 1 if omitted.
            """,
        )
        dlp = sp.add_parser("download", help="Download the question-version map.")
        dlp.add_argument(
            "csv_file", nargs="?", help="Destination filename.csv - else use default"
        )

        p = sp.add_parser("upload", help="Upload a question-version map")
        p.add_argument("csv_or_json_file")

        p = sp.add_parser(
            "append",
            help="""
                Append rows to the question-version map.
                The new paper numbers must not be in the database or you'll get an error.
            """,
        )
        p.add_argument("csv_or_json_file")
        p.add_argument(
            "--force",
            action="store_true",
            help="""
                Try to append even if papers have already been printed/scanned.
                **Caution:** you're sticking your fingers into the machinery.
                There might be various places, such as the client, that aren't
                expecting the largest paper number to increase.  All users should
                probably logout and login again.
            """,
        )

        sp.add_parser("clear", help="Clear the database of test-papers.")

    def papers_status(self) -> None:
        """Get the status of test-papers in the database."""
        n_papers = PaperInfoService().how_many_papers_in_database()
        self.stdout.write(f"{n_papers} test-papers saved to the database.")
        if PaperInfoService.is_paper_database_fully_populated():
            self.stdout.write("Database is ready")
        else:
            self.stdout.write("Database is not yet ready")

    def build_db_of_papers(
        self, *, number_to_produce: int | None = None, first: int | None = 1
    ) -> None:
        """Create a version map and use it to populate the database with papers."""
        if PaperInfoService.is_paper_database_populated():
            raise CommandError("Test-papers already saved to database - stopping.")

        self.stdout.write("Creating test-papers...")
        min_production = PQVMappingService().get_minimum_number_to_produce()
        if number_to_produce is None:
            number_to_produce = min_production
        # guard Command line input
        elif number_to_produce < 0:
            number_to_produce = min_production

        # need to assert for mypy
        assert number_to_produce is not None
        if first is None:
            qv_map = PQVMappingService().make_version_map(number_to_produce)
        else:
            qv_map = PQVMappingService().make_version_map(
                number_to_produce, first=first
            )
        try:
            PaperCreatorService.add_all_papers_in_qv_map(qv_map, background=False)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write(f"Database populated with {len(qv_map)} test-papers.")

    def clear_papers(self) -> None:
        """Remove all test-papers from the database."""
        self.stdout.write("Removing test-papers and associated tasks...")
        try:
            PaperCreatorService.remove_all_papers_from_db(background=False)
        except PlomDependencyConflict as e:
            raise CommandError(e) from e
        self.stdout.write("Database cleared of test-papers.")

    def download_pqv_map(self, dest_filename: str | None) -> None:
        # check if a populate/evacuate running
        if PaperCreatorService.is_background_chore_in_progress():
            raise CommandError("Database is being updated - try again shortly.")

        if dest_filename:
            save_path = Path(dest_filename)
        else:
            save_path = Path(PQVMappingService.get_default_csv_filename())
        if save_path.exists():
            s = f"A file exists at {save_path} - overwrite it? [y/N] "
            choice = input(s).lower()
            if choice != "y":
                self.stdout.write("Skipping.")
                return
            self.stdout.write(f"Trying to overwrite {save_path}...")
        try:
            PQVMappingService.pqv_map_to_csv(save_path)
        except ValueError as e:
            raise CommandError(e) from e
        self.stdout.write(f"Wrote {save_path}")

    def upload_pqv_map(self, f: Path) -> None:
        self.stdout.write(f"Reading qvmap from {f}")
        try:
            vm = version_map_from_file(f)
        except ValueError as e:
            raise CommandError(e)
        try:
            PaperCreatorService.add_all_papers_in_qv_map(vm, background=False)
        except (ValueError, PlomDependencyConflict, PlomDatabaseCreationError) as e:
            raise CommandError(e) from e
        self.stdout.write(f"Uploaded qvmap from {f}")

    def append_rows_to_pqv_map(self, f: Path, *, force: bool = False) -> None:
        self.stdout.write(f"Reading proposed new qvmap rows from {f}")
        try:
            vm = version_map_from_file(f)
        except ValueError as e:
            raise CommandError(e)
        try:
            PaperCreatorService.append_papers_to_qv_map(vm, force=force)
        except (
            ValueError,
            PlomDependencyConflict,
            PlomDatabaseCreationError,
            IntegrityError,
        ) as e:
            raise CommandError(f"{e} (perhaps you need to force?)") from e
        self.stdout.write(f"Uploaded qvmap from {f}")

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.papers_status()
        elif options["command"] == "build_db":
            self.build_db_of_papers(
                number_to_produce=options["number_to_produce"],
                first=options["first_paper"],
            )
        elif options["command"] == "download":
            self.download_pqv_map(options["csv_file"])
        elif options["command"] == "upload":
            self.upload_pqv_map(options["csv_or_json_file"])
        elif options["command"] == "clear":
            self.clear_papers()
        elif options["command"] == "append":
            self.append_rows_to_pqv_map(
                options["csv_or_json_file"], force=options["force"]
            )
        else:
            self.print_help("manage.py", "plom_qvmap")
