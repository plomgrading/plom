# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError

from Progress.services import ManageDiscardService


class Command(BaseCommand):
    """python3 manage.py plom_discard_pushed_page (username) -f (fixedpage pk)."""

    help = "Discard a pushed page"

    def discard_pushed_page(
        self,
        username: str,
        *,
        fixedpage_pk: int = None,
        mobilepage_pk: int = None,
        not_dry_run: bool = False,
    ):
        mds = ManageDiscardService()

        ret = mds.discard_pushed_page_cmd(
            username,
            fixedpage_pk=fixedpage_pk,
            mobilepage_pk=mobilepage_pk,
            dry_run=not not_dry_run,
        )
        print(ret)

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
            "--do-it",
            action="store_true",
            help="",
        )

    def handle(self, *args, **options):
        self.discard_pushed_page(
            options["username"],
            fixedpage_pk=options["fixed"],
            mobilepage_pk=options["mobile"],
            not_dry_run=options["do_it"],
        )
