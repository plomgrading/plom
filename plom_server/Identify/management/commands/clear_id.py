# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from ...services import IDProgressService


class Command(BaseCommand):
    """Command tool for clearing certain ID paper number or all ID papers.

    python3 manage.py clear_id (paper_num)
    python3 manage.py clear_id all
    """

    help = """Clear the ID of a specific paper or clear all IDs."""

    def specific_id(self, paper_num):
        try:
            IDProgressService().clear_id_from_paper(paper_num)
            self.stdout.write(f"Cleared ID for paper number #{paper_num}")
        except ObjectDoesNotExist as err:
            raise CommandError(err)

    def clear_all_ids(self):
        try:
            IDProgressService().clear_id_from_all_identified_papers()
            self.stdout.write("All IDs cleared.")
        except ObjectDoesNotExist as err:
            raise CommandError(err)

    def add_arguments(self, parser):
        parser.add_argument(
            "paper_num", type=str, help="Enter a specific paper number or all."
        )

    def handle(self, *args, **options):
        if options["paper_num"].isnumeric():
            self.specific_id(options["paper_num"])
        elif options["paper_num"] == "all":
            self.clear_all_ids()
        else:
            self.print_help("manage.py", "clear_id")
