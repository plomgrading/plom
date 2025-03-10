# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import shutil

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ...services import database_service


class Command(BaseCommand):
    """Remove old files and database, then regenerate minimal needed.

    Removes old user-generated files, migrations, the database,
    huey-process database. Then instantiates a new database, rebuilds
    the migrations, and runs them.
    """

    def remove_misc_user_files(self):
        """Remove any user-generated files from django's MEDIA directory."""
        print("Removing any user-generated files from django's MEDIA_ROOT directory")
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def remove_old_migration_files(self):
        """Remove old db migration files from the source tree.

        Caution: this assumes we have read-write access to the source code!
        """
        print("Avoid perplexing errors by removing autogen migration droppings")
        for path in settings.BASE_DIR.glob("*/migrations/*.py"):
            if path.name == "__init__.py":
                continue
            else:
                print(f"Removing {path}")
                path.unlink(missing_ok=True)

    def huey_cleanup(self):
        """Remove any existing huey db."""
        for path in settings.PLOM_BASE_DIR.glob("hueydb*.sqlite*"):
            print(f"Removing {path}")
            path.unlink(missing_ok=True)

    def handle(self, *args, **options):
        """Clean up source tree, remove old DB and huey files, and rebuild db."""
        self.stdout.write("Removing old files, database, huey-db.")
        self.remove_misc_user_files()
        self.remove_old_migration_files()
        self.huey_cleanup()
        database_service.drop_database()

        self.stdout.write("Rebuilding database and migrations.")
        database_service.create_database()
        self.stdout.write("Database build was run.")
        call_command("makemigrations")
        call_command("migrate")
        self.stdout.write("migrations have been run.")
        self.stdout.write("Note: neither server nor huey are running yet.")
        self.stdout.write("Note: no groups or users have been created yet.")
