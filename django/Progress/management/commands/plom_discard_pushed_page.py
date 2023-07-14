# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError

from Progress.services import ManageDiscardService


class Command(BaseCommand):
    """python3 manage.py plom_discard_pushed_page (username) (papernumber) -f (fixedpage number)."""

    help = "Discard a pushed page"

    def discard_pushed_page(self, username:str, papernumber:int):
        mds = ManageDiscardService()

        ret = mds.discard_pushed_page_cmd(username, papernumber)
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

    def handle(self, *args, **options):
        self.discard_pushed_page(
            options["username"],
            options["papernumber"],
        )
