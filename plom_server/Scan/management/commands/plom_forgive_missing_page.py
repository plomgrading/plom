# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ...services import ForgiveMissingService


class Command(BaseCommand):
    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument(
            "username",
            type=str,
            help="The username of the user forgiving the missing page",
        )
        parser.add_argument(
            "paper_number", type=int, help="The paper which is missing the page"
        )
        parser.add_argument(
            "page_number", type=int, help="The page missing from the paper"
        )

    def handle(self, *args, **opt) -> None:
        try:
            ForgiveMissingService.forgive_missing_fixed_page_cmd(
                opt["username"], opt["paper_number"], opt["page_number"]
            )
            self.stdout.write(
                f"Replaced missing page {opt['page_number']} from paper {opt['paper_number']} with a substitute image."
            )
        except ValueError as err:
            raise CommandError(err)
