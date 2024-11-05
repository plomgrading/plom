# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.test.client import RequestFactory
from django.db.models import Q

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

    def create_users_from_file(self, file_path: Path) -> None:
        """Creates users defined in a file.

        .csv file must contain fields "username" and "usergroup".
        """
        # TODO: move this into service[s]
        #######################
        # TODO: unit tests
        with open(file_path) as csvfile:
            new_user_list = list(csv.DictReader(csvfile))

        required_fields = set(["username", "usergroup"])
        if not required_fields.issubset(new_user_list[0].keys()):
            raise CommandError(
                f".csv is missing required fields, it must contain: {required_fields}"
            )

        # lots of checks before creating new users, don't want to fail midway
        new_usernames = [u["username"] for u in new_user_list]
        # check no duplicates among new users
        if len(set([u.lower() for u in new_usernames])) != len(new_usernames):
            raise CommandError(
                "your .csv contains duplicate users, case doesn't distinguish them"
            )
        # check against existing users, case insensitive makes this tricky
        # https://stackoverflow.com/questions/14907525/how-can-i-chain-djangos-in-and-iexact-queryset-field-lookups
        q_list = Q()
        for q in [Q(username__iexact=n) for n in new_usernames]:
            q_list |= q
        collisions = User.objects.filter(q_list)
        if collisions.exists():
            collisions = list(collisions.values_list("username", flat=True))
            raise CommandError(f"The following users already exist: {collisions}")

        AuS = AuthenticationServices()
        # TODO: auth service needs batch user creation in one DB call
        for index, user_dict in enumerate(new_user_list):
            AuS.create_user_and_add_to_group(
                user_dict["username"], user_dict["usergroup"]
            )
            # TODO: if --raw-password, append a password instead of a link
            rf = RequestFactory()
            # serverside env variables correct
            # for shoddy dummy request, see `generate_link()`.
            dummy_request = rf.post("/submit/", {"foo": "bar"})
            # SERVER_NAME is checked by Django, choice is important.
            dummy_request.META["SERVER_NAME"] = settings.ALLOWED_HOSTS[0]

            user = User.objects.get(username=user_dict["username"])
            user_dict["reset_link"] = AuS.generate_link(dummy_request, user)

        with io.StringIO() as iostream:
            writer = csv.DictWriter(
                iostream,
                fieldnames=list(new_user_list[0].keys()),
            )
            writer.writeheader()
            writer.writerows(new_user_list)
            csv_string = iostream.getvalue()  # return this

        #########################
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
            poorly defined or duplicate users will fail the command.
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
            self.create_users_from_file(options["file"])
        elif options["list"]:
            self.list_users()
        else:
            self.list_users()
