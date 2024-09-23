# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanService

from plom.plom_exceptions import PlomBundleLockedException


class Command(BaseCommand):
    """Management command that contains several subcommands.

    python3 manage.py plom_bundle_push_lock status
    python3 manage.py plom_bundle_push_lock lock bundle name
    python3 manage.py plom_bundle_push_lock unlock bundle name
    """

    help = "Show or toggle the push-lock of staging bundles"

    def show_lock_status(self):
        lock_info = ScanService().get_bundle_push_lock_information(include_pushed=False)
        self.stdout.write(
            tabulate(lock_info, headers="firstrow", tablefmt="simple_outline")
        )

    def push_lock_bundle(self, bundle_name):
        try:
            ScanService().push_lock_bundle_cmd(bundle_name)
        except ValueError as err:
            raise CommandError(err)
        except PlomBundleLockedException as err:
            raise CommandError(err)

        self.show_lock_status()

    def push_unlock_bundle(self, bundle_name):
        try:
            ScanService().push_unlock_bundle_cmd(bundle_name)
        except ValueError as err:
            raise CommandError(err)

        self.show_lock_status()

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="View or toggle push-lock.",
        )
        sp.add_parser("status", help="Show the lock status of the staging bundles.")
        sp_lock = sp.add_parser("lock", help="Set the given bundle as push-locked")
        sp_lock.add_argument(
            "bundle_name",
            type=str,
            nargs=1,
            help="Set the given bundle as push-locked",
        )
        sp_unlock = sp.add_parser("unlock", help="Set the given bundle as push-locked")
        sp_unlock.add_argument(
            "bundle_name",
            type=str,
            nargs=1,
            help="Set the given bundle as not push-locked",
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_lock_status()
        elif options["command"] == "lock":
            self.push_lock_bundle(bundle_name=options["bundle_name"][0])
        elif options["command"] == "unlock":
            self.push_unlock_bundle(bundle_name=options["bundle_name"][0])
        else:
            self.print_help("manage.py", "plom_staging_bundles")
