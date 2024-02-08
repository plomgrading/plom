# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald

import os

from plom.aliceBob import simple_password

from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser, CommandError

from ...services import DemoProcessesService


class Command(BaseCommand):
    """Initialize a plom server for production.

    Creates a new database and tables, the Huey queue, user groups, and
    admin and manager users.
    """

    def wait_for_exit(self):
        while True:
            x = input("Type 'quit' and press Enter to exit the demo: ")
            if x.casefold() == "quit":
                break

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--no-waiting",
            action="store_true",
            help="Do not wait for user input at the end of the init sequence before stopping the development server.",
        )

        parser.add_argument(
            "--port",
            action="store",
        )

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
        if User.objects.filter(is_superuser=True).count() > 0:
            raise CommandError("Cannot initialize server - superuser already exists.")

        if not Group.objects.filter(name="admin").exists():
            raise CommandError("Cannot initialize server - admin group not created.")

        admin = User.objects.create_superuser(username=username, password=password)
        admin_group = Group.objects.get(name="admin")
        admin.groups.add(admin_group)
        admin.save()

    def create_manager(self, username: str, password: str) -> None:
        """Create a manager user."""
        if not Group.objects.filter(name="manager").exists():
            raise CommandError("Cannot initialize server - manager group not created.")

        # TODO: more efficient way to query?
        for user in User.objects.all():
            if user.groups.filter(name="manager").exists():
                raise CommandError(
                    "Cannot initialize server - manager user already exists."
                )

        manager = User.objects.create_user(username=username, password=password)
        manager_group = Group.objects.get(name="manager")
        manager.groups.add(manager_group)
        manager.save()

    def handle(self, *args, **options):
        # database and Huey
        proc_service = DemoProcessesService()
        proc_service.initialize_server_and_db()

        # make user groups
        call_command("plom_create_groups")

        # generate random passwords if no info is provided via the commandline
        if options["admin_login"] is None:
            print("No admin login details provided: autogenerating...")
            admin_username = "admin"
            admin_password = simple_password(6)
            print(
                f"Admin username: {admin_username}\n"
                f"Admin password: {admin_password}\n"
            )
        else:
            admin_username, admin_password = options["admin_login"]
        self.create_admin(username=admin_username, password=admin_password)

        if options["manager_login"] is None:
            print("No manager login details provided: autogenerating...")
            manager_username = "manager"
            manager_password = simple_password(6)
            print(
                f"Manager username: {manager_username}\n"
                f"Manager password: {manager_password}\n"
            )
        else:
            manager_username, manager_password = options["manager_login"]
        self.create_manager(username=manager_username, password=manager_password)

        if options["no_waiting"]:
            return

        huey_worker_proc = None
        server_proc = None
        try:
            # launch Huey queue in the background
            huey_worker_proc = proc_service.launch_huey_workers()

            # run the development server (TODO: for now)
            port = int(os.environ.get("PLOM_CONTAINER_PORT", "8000"))
            server_proc = proc_service.launch_server(port=port)

            # wait for the user to quit, then end the background processes
            self.wait_for_exit()
        finally:
            if huey_worker_proc is not None:
                huey_worker_proc.terminate()
            if server_proc is not None:
                server_proc.terminate()
