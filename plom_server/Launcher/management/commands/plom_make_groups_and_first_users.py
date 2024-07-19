# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from django.contrib.auth.models import User, Group

from plom.aliceBob import simple_password


class Command(BaseCommand):
    """Build user groups, the admin and manager users."""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--admin-login",
            nargs=2,
            help="Login details for the admin. Format: --admin-login USERNAME PASSWORD",
        )
        parser.add_argument(
            "--manager-login",
            nargs=2,
            help="Login details for the manager. Format: --manager-login USERNAME PASSWORD",
        )

    def create_admin(self, username: str, password: str) -> None:
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

    def create_manager(self, username: str, password: str) -> None:
        """Create a manager user."""
        with transaction.atomic(durable=True):
            try:
                manager_group = Group.objects.get(name="manager")
            except ObjectDoesNotExist:
                raise CommandError(
                    "Cannot create a manager-user since the manager-group has not been created."
                )

            if User.objects.filter(groups__name="manager").exists():
                raise CommandError(
                    "Cannot initialize server - manager user already exists."
                )

            manager = User.objects.create_user(username=username, password=password)
            manager.groups.add(manager_group)
            manager.save()

    def handle(self, *args, **options):
        self.stdout.write("Make user groups")
        call_command("plom_create_groups")

        # generate random passwords if no info is provided via the commandline
        self.stdout.write("Make admin user")
        if options["admin_login"] is None:
            self.stdout.write("No admin login details provided: autogenerating...")
            admin_username = "admin"
            admin_password = simple_password(6)
            self.stdout.write(
                f"Admin username: {admin_username}\n"
                f"Admin password: {admin_password}\n"
            )
        else:
            admin_username, admin_password = options["admin_login"]
        self.create_admin(username=admin_username, password=admin_password)

        self.stdout.write("Make manager user")
        if options["manager_login"] is None:
            self.stdout.write("No manager login details provided: autogenerating...")
            manager_username = "manager"
            manager_password = simple_password(6)
            self.stdout.write(
                f"Manager username: {manager_username}\n"
                f"Manager password: {manager_password}\n"
            )
        else:
            manager_username, manager_password = options["manager_login"]
        self.create_manager(username=manager_username, password=manager_password)
