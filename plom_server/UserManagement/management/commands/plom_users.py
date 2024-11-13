# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from Authentication.services import AuthenticationServices

from ...services import UsersService

from pathlib import Path
from tabulate import tabulate
import csv
import io


class Command(BaseCommand):
    """Show and manipulate non-admin users.

    Toggle markers/lead_markers, import users, list users.
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

    def handle_import(self, file_path: Path, *, set_password: bool = False) -> None:
        """Imports users from a file.

        Input file must be a .csv containing fields: 'username', 'usergroup'
        created users are written to stdout in the format of a .csv.
        """
        try:
            new_user_list = AuthenticationServices().create_users_from_csv(file_path)
        except (IntegrityError, ObjectDoesNotExist, KeyError) as e:
            raise CommandError(e)

        with io.StringIO() as iostream:
            writer = csv.DictWriter(
                iostream,
                fieldnames=list(new_user_list[0].keys()),
            )
            writer.writeheader()
            writer.writerows(new_user_list)
            csv_string = iostream.getvalue()
        self.stdout.write(csv_string)

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List users on the system (default behaviour if nothing else specified).",
        )

        sub = parser.add_subparsers(
            title="subcommands", dest="subcommand", required=False
        )

        import_users = sub.add_parser(
            "import",
            help="Create specific users en-masse.",
            description="""Create users specified in a .csv file,
            poorly defined or duplicated users will fail the command.
            """,
        )
        import_users.add_argument(
            "file",
            help="""
                A path to the .csv file specifying new users.

                Should contain fields "username","usergroup".
            """,
        )

    def handle(self, *args, **options):
        if options["subcommand"] == "import":
            self.handle_import(options["file"])
        elif options["list"]:
            self.list_users()
        else:
            self.list_users()
