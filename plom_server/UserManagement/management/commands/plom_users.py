# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024, 2026 Aidan Murphy

import csv
import io
from pathlib import Path
from tabulate import tabulate

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import IntegrityError

from plom_server.Authentication.services import AuthService
from ...services import UsersService


class Command(BaseCommand):
    """Show and manipulate users."""

    def list_users(self) -> None:
        user_list = UsersService.get_list_of_user_info()

        if not user_list:
            self.stdout.write("no users found.")
            return

        self.stdout.write(str(tabulate(user_list, headers="keys")))

    def handle_import(self, file_path: Path, *, set_password: bool = False) -> None:
        """Imports users from a csv file and display to stdout."""
        try:
            new_user_list = AuthService.create_users_from_csv(file_path)
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

    def create_password_reset_link(self, uid: int) -> None:
        """Create a password reset link for the specified user, write to stdout."""
        user_obj = User.objects.get(id=uid)
        reset_link = AuthService.generate_link(user_obj, port="8000")
        self.stdout.write(reset_link)

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            title="subcommands", dest="subcommand", required=False
        )

        create_password_reset_link = sub.add_parser(
            "create-password-reset-link",
            help="Create a password reset link for a Plom user account.",
            description="""Requires the user's database id.
            """,
        )
        create_password_reset_link.add_argument(
            "uid",
            type=int,
            help="The user's database ID.",
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

                Should contain fields "username", "usergroup".
            """,
        )

        sub.add_parser(
            "list",
            help="List users on the system.",
            description="""User information is taken directly from the database.
                Some understanding of Plom's internals may be required to parse it.
            """,
        )

    def handle(self, *args, **options):
        if options["subcommand"] == "import":
            self.handle_import(options["file"])
        elif options["subcommand"] == "create-password-reset-link":
            self.create_password_reset_link(options["uid"])
        elif options["subcommand"] == "list":
            self.list_users()
        else:
            self.print_help()
