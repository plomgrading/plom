# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from plom.aliceBob import simple_password

from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser

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

    def handle(self, *args, **options):
        # database and Huey
        proc_service = DemoProcessesService()
        proc_service.initialize_server_and_db()

        # make user groups
        call_command("plom_create_groups")

        # make an admin user
        admin_password = simple_password(3)
        admin = User.objects.create_superuser(username="admin", password=admin_password)
        admin_group = Group.objects.get(name="admin")
        admin.groups.add(admin_group)
        admin.save()

        # make a manager user
        manager_password = simple_password(3)
        manager = User.objects.create(username="manager", password=manager_password)
        manager_group = Group.objects.get(name="manager")
        manager.groups.add(manager_group)
        manager.save()

        # TODO: Find an alternative to printing passwords to stdout. Log file instead?
        self.stdout.write("*" * 10)
        self.stdout.write(f"Admin username: admin\nAdmin password: {admin_password}\n")
        self.stdout.write(
            f"Manager username: manager\nManager password: {manager_password}"
        )
        self.stdout.write("*" * 10)

        if options["no_waiting"]:
            return

        try:
            # launch Huey queue in the background
            huey_worker_proc = proc_service.launch_huey_workers()

            # run the development server (TODO: for now)
            server_proc = proc_service.launch_server(port=8000)

            # wait for the user to quit, then end the background processes
            self.wait_for_exit()
        finally:
            huey_worker_proc.terminate()
            server_proc.terminate()
