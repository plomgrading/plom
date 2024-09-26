# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer

from pathlib import Path
import shutil
import subprocess
from shlex import split

from django.core.management import call_command
from django.conf import settings

from Base.services import database_service


class LaunchProcessesService:
    """Handle starting and stopping the server and the Huey background process."""

    def remove_misc_user_files(self, engine):
        """Remove any user-generated files from django's media directory."""
        print("Removing any user-generated files from django's MEDIA_ROOT directory")
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def rebuild_migrations_and_migrate(self, engine):
        """Rebuild the database migrations and run them."""
        # print("Rebuild the database migrations and migrate")
        call_command("makemigrations")
        call_command("migrate")

    def _huey_cleanup(self):
        # TODO: cleanup from older huey run; for now removes a hardcoded database
        for path in Path("huey").glob("hueydb*.sqlite*"):
            path.unlink(missing_ok=True)

    def launch_server(self, *, port):
        """Launch django's development server on the given port."""
        print(f"Launching django server on localhost port {port}")
        # this needs to be run in the background
        cmd = f"python3 manage.py runserver {port}"
        return subprocess.Popen(split(cmd))

    def remove_old_migration_files(self):
        """Remove any old migrations from the source tree."""
        print("Avoid perplexing errors by removing autogen migration droppings")

        for path in Path(".").glob("*/migrations/*.py"):
            if path.name == "__init__.py":
                continue
            else:
                print(f"Removing {path}")
                path.unlink(missing_ok=True)

    def initialize_server_and_db(self):
        """Configure Django settings and flush the previous database and media files."""
        engine = database_service.get_database_engine()
        print(f"You appear to be running with a {engine} database.")

        print("*" * 40)
        self.remove_old_migration_files()

        print("*" * 40)
        self.remove_misc_user_files(engine)
        self._huey_cleanup()

        print("*" * 40)
        database_service.drop_database()
        database_service.create_database()

        print("*" * 40)
        self.rebuild_migrations_and_migrate(engine)
