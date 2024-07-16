# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from django.core.management.base import BaseCommand, CommandError

from Papers.services import PaperCreatorService, PaperInfoService
from Preparation.services import PQVMappingService


class Command(BaseCommand):
    help = "Display the current state of test-papers in the database, populate the test-paper database, or clear."

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command", description="Display, populate, or clear test-papers."
        )
        sp.add_parser(
            "status", help="Show the current state of test-papers in the database."
        )

        sp.add_parser(
            "build_db",
            help="""
                Populate the database with test-papers using information
                provided in the spec and QV-map.
                Also constructs the associate pdf-build tasks.
            """,
        )

        sp.add_parser("clear", help="Clear the database of test-papers.")

    def papers_status(self):
        """Get the status of test-papers in the database."""
        pqvs = PQVMappingService()
        if not pqvs.is_there_a_pqv_map():
            self.stdout.write("Question-version map not present.")
            return
        qv_map_len = len(pqvs.get_pqv_map_dict())

        paper_info = PaperInfoService()
        n_papers = paper_info.how_many_papers_in_database()
        self.stdout.write(f"{n_papers} test-papers saved to the database.")
        if qv_map_len == n_papers:
            self.stdout.write("Database is ready")
        else:
            self.stdout.write(f"Database still requires {qv_map_len - n_papers} papers")

    def build_papers(self):
        """Write test-papers to the database, so long as the Papers table is empty and a QV map is present."""
        pqvs = PQVMappingService()
        if not pqvs.is_there_a_pqv_map():
            self.stderr.write("No question-version map found - stopping.")
            return

        paper_info = PaperInfoService()
        if paper_info.is_paper_database_populated():
            self.stderr.write("Test-papers already saved to database - stopping.")
            return

        self.stdout.write("Creating test-papers...")
        pcs = PaperCreatorService()
        qv_map = pqvs.get_pqv_map_dict()
        try:
            pcs.add_all_papers_in_qv_map(qv_map, background=False)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write(f"Database populated with {len(qv_map)} test-papers.")

    def clear_papers(self):
        """Remove all test-papers from the database."""
        paper_info = PaperInfoService()
        if paper_info.how_many_papers_in_database() == 0:
            self.stdout.write("No test-papers found in database - stopping.")
            return

        self.stdout.write("Removing test-papers and associated tasks...")
        # note when a paper is deleted its associated task is also deleted.
        PaperCreatorService().remove_all_papers_from_db(background=False)
        self.stdout.write("Database cleared of test-papers.")

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.papers_status()
        elif options["command"] == "build_db":
            self.build_papers()
        elif options["command"] == "clear":
            self.clear_papers()
        else:
            self.print_help("manage.py", "plom_papers")
