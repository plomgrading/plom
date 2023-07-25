# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand

from Progress.services import ManageDiscardService


class Command(BaseCommand):
    """python3 manage.py plom_discard_pushed_page (username) -f (fixedpage pk)."""

    help = (
        "Discard a pushed page. Note that at present this can only discard dnm pages."
    )

    def discard_pushed_page(
        self,
        username: str,
        *,
        fixedpage_pk: int | None = None,
        mobilepage_pk: int | None = None,
        really_do_it: bool = False,
    ):
        mds = ManageDiscardService()

        ret = mds.discard_pushed_page_cmd(
            username,
            fixedpage_pk=fixedpage_pk,
            mobilepage_pk=mobilepage_pk,
            dry_run=not really_do_it,
        )
        self.stdout.write(ret)

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="The user performing this operation"
        )
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "-f",
            "--fixed",
            type=int,
            help="The pk of the fixedpage to be discarded",
        )
        grp.add_argument(
            "-m",
            "--mobile",
            type=int,
            help="The pk of the mobilepage to be discarded",
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="By default this command does a dry-run of the discard. Add this flag to actually do the discard.",
        )

    def handle(self, *args, **options):
        self.discard_pushed_page(
            options["username"],
            fixedpage_pk=options["fixed"],
            mobilepage_pk=options["mobile"],
            really_do_it=options["yes"],
        )
