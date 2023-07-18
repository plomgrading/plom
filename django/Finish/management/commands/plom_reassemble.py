# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.core.management.base import BaseCommand, CommandError

from Finish.services import ReassembleService
from Papers.services import PaperInfoService, SpecificationService
from Papers.models import Paper


class Command(BaseCommand):
    """Generate reassembled test-papers with TA annotations from the command line."""

    help = "Create PDFs to return to students"

    def add_arguments(self, parser):
        parser.add_argument(
            "testnum",
            type=int,
            nargs="?",
            help="Which test paper to reassemble (optional)",
        )

    def reassemble_one_paper(self, test_num):
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")
        if not paper_service.is_this_paper_in_database(test_num):
            raise CommandError(f"Paper number {test_num} does not exist - stopping.")

        paper = Paper.objects.get(paper_number=test_num)
        reassembler = ReassembleService()

        reassembler.reassemble_paper(paper, SpecificationService().get_shortname)

    def handle(self, *args, **options):
        test_num = options["testnum"]
        if test_num:
            self.stdout.write(f"Building test {test_num}...")
            self.reassemble_one_paper(test_num)
        else:
            self.stdout.write("Building all papers!")
