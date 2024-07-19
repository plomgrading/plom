# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    """Initialize a plom server for production.

    Creates a new database and tables, the Huey queue, user groups, and
    admin and manager users.

    Note - hopefully deprecated in future and replaces with
    script that calls constituent commands?
    """

    def wait_for_exit(self):
        while True:
            x = input("Type 'quit' and press Enter to shutdown the server: ")
            if x.casefold() == "quit":
                break

    def add_arguments(self, parser: CommandParser) -> None:
        # this is only ever called with --no-waiting,
        # so deleted optional args for port, and
        # admin- and manager-logins
        parser.add_argument(
            "--no-waiting",
            action="store_true",
            help="Do not wait for user input at the end of the init sequence before stopping the development server.",
        )

    def handle(self, *args, **options):
        # database and Huey
        call_command("plom_clean_all_and_build_db")
        call_command("plom_make_groups_and_first_users")
