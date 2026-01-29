# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024, 2026 Colin B. Macdonald

import sys

from django.core.management.base import BaseCommand, CommandParser, CommandError

from ...services import database_service


class Command(BaseCommand):
    """High level database operations such as listing tables or checking existence."""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check-for-database",
            action="store_true",
            help="Check if a database exists, and exit with nonzero if it does.",
        )
        parser.add_argument(
            "--create-database",
            action="store_true",
            help="""
                Create a new database.
                Note you must "migrate" after calling this.  Then follow-up
                with "--create-database-metadata".
            """,
        )
        parser.add_argument(
            "--create-database-metadata",
            action="store_true",
            help="""
                Record the current Plom version as creating the database,
                set the version, etc.  You should call this after (1) calling
                "--create-database" and (2) running "migrate".  Why don't we
                automate this little three-step dance?  Well "migrate" isn't
                a Plom command...
            """,
        )
        parser.add_argument(
            "--update-database-metadata",
            action="store_true",
            help="""
                Record the current Plom version as the last one to access this
                database.  This should be called before or after you use the
                database with Plom.  It does not need to be set with every
                single write (and should not be!).  Its enough to set this on
                startup.  Its not a problem if you don't actually change the
                database other than calling this.
            """,
        )
        parser.add_argument(
            "--check-database",
            action="store_true",
            help="Check whether the current database is appropriate, based on its version.",
        )
        parser.add_argument(
            "--drop-database",
            action="store_true",
            help="Completely erase the database: DANGEROUS!",
        )
        parser.add_argument(
            "--yes",
            "-y",
            action="store_true",
            help="""
                Don't ask interactively when doing dangerous things such
                as dropping databases.
            """,
        )

    def handle(self, *args, **options):
        if options["check_for_database"]:
            r = database_service.is_there_a_database()
            if r:
                sys.exit(1)
            sys.exit(0)
        elif options["create_database"]:
            database_service.create_database()
        elif options["create_database_metadata"]:
            database_service.created_record_plom_version()
        elif options["update_database_metadata"]:
            database_service.update_last_used_plom_version()
        elif options["check_database"]:
            database_service.check_database_version()
        elif options["drop_database"]:
            if options["yes"]:
                yes = True
            else:
                yes = (
                    input(
                        "Are you sure you want to completely erase the "
                        "database? (Type 'yes' to continue) "
                    )
                    == "yes"
                )
            if yes:
                database_service.drop_database()
        else:
            raise CommandError("Need to provide an argument")
