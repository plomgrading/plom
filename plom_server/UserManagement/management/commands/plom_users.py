# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand

from ...services import UsersService

from tabulate import tabulate


class Command(BaseCommand):
    """Show users membership of the marker and lead markers groups.

    Also allow toggling of membership of the lead-marker group.
    """

    def list_users(self) -> None:
        user_info: dict = UsersService.get_user_info()

        if not any(user_info.values()):
            self.stdout.write("no users found.")
            return

        # reshape user_info into something more extensible
        user_list = []
        for user_group, users in user_info.items():
            for user in users:
                user_list.append([user, user_group, user.last_login])

        self.stdout.write(str(tabulate(user_list, tablefmt="simple")))

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
