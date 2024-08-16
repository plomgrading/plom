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
            help="The username of the user forgiving all missing dnm pages",
        )
        parser.add_argument(
            "--do-it",
            action="store_true",
            default=False,
            help="Actually forgive the pages. By default, simply list the DNM pages that are missing.",
        )

    def forgive_all_missing_dnm_pages(
        self, username: str, *, do_it: bool = False
    ) -> None:
        list_of_missing_dnm = ForgiveMissingService.get_list_of_all_missing_dnm_pages()
        self.stdout.write(f"These are the missing DNM pages: {list_of_missing_dnm}")
        if do_it:
            self.stdout.write("Are you sure? Please enter 'Forgiveness' to proceed.")
            really = input()
            if really == "Forgiveness":
                for dat in list_of_missing_dnm:
                    pn = dat["paper_number"]
                    pg = dat["page_number"]
                    ForgiveMissingService.forgive_missing_fixed_page_cmd(
                        username, pn, pg
                    )
                    self.stdout.write(f"Replaced missing DNM page-{pg} of paper-{pn}.")
            else:
                self.stdout.write("Not replacing papers. Stopping.")

    def handle(self, *args, **opt) -> None:
        try:
            self.forgive_all_missing_dnm_pages(opt["username"], do_it=opt["do_it"])
        except ValueError as err:
            raise CommandError(err)
