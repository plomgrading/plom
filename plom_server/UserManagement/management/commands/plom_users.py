# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import UsersService


class Command(BaseCommand):
    """Show users membership of the marker and lead markers groups.

    Also allow toggling of membership of the lead-marker group.
    """

    def list_users(self) -> None:
        print("TODO")
        print(UsersService.get_user_info())
        if False:
            CommandError("foo")

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List users on the system (default behaviour if nothing else specified).",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self.list_users()
        else:
            self.list_users()
