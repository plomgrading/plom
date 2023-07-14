# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError

from Progress.services import ManageDiscardService


class Command(BaseCommand):
    """python3 manage.py plom_discard_pushed_page (username) (papernumber) -f (fixedpage number)."""

    help = "Discard a pushed page"

    def discard_pushed_page(
        self,
        username: str,
        papernumber: int,
        *,
        image_pk=None,
        fixedpage_number=None,
        mobilepage_number=None,
        not_dry_run=False,
    ):
        mds = ManageDiscardService()

        ret = mds.discard_pushed_page_cmd(
            username,
            papernumber,
            image_pk=image_pk,
            fixedpage_number=fixedpage_number,
            mobilepage_number=mobilepage_number,
            dry_run=not not_dry_run,
        )
        print(ret)

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="The user performing this operation"
        )
        parser.add_argument(
            "papernumber",
            type=int,
            help="The paper containing the page to be discarded",
        )
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "-i", "--image", type=int, help="The pk of the image to be discarded"
        )
        grp.add_argument(
            "-f",
            "--fixed",
            type=int,
            help="The number of the fixedpage to be discarded",
        )
        grp.add_argument(
            "-m",
            "--mobile",
            type=int,
            help="The number of the mobilepage to be discarded",
        )
        parser.add_argument(
            "--do-it",
            action="store_true",
            help="",
        )

    def handle(self, *args, **options):
        self.discard_pushed_page(
            options["username"],
            options["papernumber"],
            image_pk=options["image"],
            fixedpage_number=options["fixed"],
            mobilepage_number=options["mobile"],
            not_dry_run=options["do_it"],
        )
