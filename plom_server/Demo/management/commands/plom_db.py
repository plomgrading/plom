# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

import sys

from django.core.management.base import BaseCommand, CommandParser, CommandError

from ...services import DemoProcessesService


class Command(BaseCommand):
    """High level database operations such as listing tables or checking existence."""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check-for-database",
            action="store_true",
            help="Check if a database exists, and exit with nonzero if it does,",
        )

    def handle(self, *args, **options):
        if options["check_for_database"]:
            r = DemoProcessesService().is_there_a_database()
            if r:
                sys.exit(1)
            sys.exit(0)
        raise CommandError("Need to provide an argument")
