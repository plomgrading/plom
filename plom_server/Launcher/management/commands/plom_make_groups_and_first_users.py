# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.db import transaction

from django.contrib.auth.models import User, Group

from plom.aliceBob import simple_password
from plom_server.Authentication.services import AuthService


class Command(BaseCommand):
    """Build user groups, the admin and manager users."""

    def add_arguments(self, parser: CommandParser) -> None:
        """Process commandline arguments."""
        parser.add_argument(
            "--admin-login",
            nargs=2,
            metavar=("USERNAME", "PASSWORD"),
            help="Login details for the admin.",
        )
        parser.add_argument(
            "--manager-login",
            nargs=2,
            metavar=("USERNAME", "PASSWORD"),
            help="Login details for the manager.",
        )
        parser.add_argument(
            "--force-passwords",
            action="store_true",
            help="""
                Set simple passwords and write them to stdout, rather than
                password reset links.
            """,
        )

    def create_admin(self, username: str, password: str | None = None) -> User:
        """Create an admin user."""
        with transaction.atomic(durable=True):
            if User.objects.filter(is_superuser=True).count() > 0:
                raise CommandError("Cannot create admin-user, they already exist.")

            if not Group.objects.filter(name="admin").exists():
                raise CommandError(
                    "Cannot create admin-user since the admin group has not been created."
                )

            admin = User.objects.create_superuser(username=username, password=password)
            admin_group = Group.objects.get(name="admin")
            admin.groups.add(admin_group)
            admin.save()
            return admin

    def create_first_manager(
        self, username: str, *, password: str | None = None
    ) -> User:
        """Create a manager user."""
        if User.objects.filter(groups__name="manager").exists():
            raise CommandError(
                "Cannot initialize server - manager user already exists."
            )
        try:
            return AuthService.create_manager_user(username, password=password)
        except ValueError as e:
            raise CommandError(e) from None

    def handle(self, *args, **options):
        """Make groups and users for the plom-server."""
        self.stdout.write("Make user groups")
        call_command("plom_create_groups")

        # generate passwords if no info is provided via the commandline
        manager_string = "Make manager user\n"
        if options["manager_login"] is None:
            manager_string += "No manager login details provided: autogenerating...\n"
            manager_username = "manager"
            # check if passwords should be generated, or reset links should be provided
            if options["force_passwords"]:
                manager_password = simple_password(6)
                self.create_first_manager(manager_username, password=manager_password)
            else:
                manager_obj = self.create_first_manager(manager_username)
                manager_password = AuthService.generate_link(manager_obj, port="8000")
            manager_string += "v" * 40 + "\n"
            manager_string += f"Manager username: {manager_username}\n"
            manager_string += f"Manager password: {manager_password}\n"
            manager_string += "^" * 40 + "\n"
        else:
            manager_username, manager_password = options["manager_login"]
            self.create_first_manager(manager_username, password=manager_password)
        self.stdout.write(manager_string)

        admin_string = "Make admin user\n"
        if options["admin_login"] is None:
            admin_string += "No admin login details provided: autogenerating...\n"
            admin_username = "admin"
            # check if passwords should be generated, or reset links should be provided
            if options["force_passwords"]:
                admin_password = simple_password(6)
                self.create_admin(username=admin_username, password=admin_password)
            else:
                admin_obj = self.create_admin(username=admin_username)
                admin_password = AuthService.generate_link(admin_obj, port="8000")
            admin_string += "v" * 40 + "\n"
            admin_string += f"Admin username: {admin_username}\n"
            admin_string += f"Admin password: {admin_password}\n"
            admin_string += "^" * 40 + "\n"
        else:
            admin_username, admin_password = options["admin_login"]
            self.create_admin(username=admin_username, password=admin_password)
        self.stdout.write(admin_string)
