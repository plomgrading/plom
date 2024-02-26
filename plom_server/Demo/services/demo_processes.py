# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from pathlib import Path
import shutil
import subprocess
from shlex import split

from django.core.management import call_command
from django.conf import settings

from . import database_service


class DemoProcessesService:
    """Handle starting and stopping the server and the Huey background process."""

    def remove_old_db_and_misc_user_files(self, engine):
        print("Removing old DB and any misc user-generated files")

        if engine == "sqlite":
            database_service.sqlite_delete_database()
        elif engine == "postgres":
            database_service.recreate_postgres_database()
        else:
            raise RuntimeError('Unexpected engine "{engine}"')

        # TODO: Issue #2926:  where should these live?  And there are three
        # hardcoded here but seems to me the toml could specify something else...
        for fname in [
            "fake_bundle1.pdf",
            "fake_bundle2.pdf",
            "fake_bundle3.pdf",
        ]:
            Path(fname).unlink(missing_ok=True)

        for path in Path("huey").glob("huey_db.*"):
            path.unlink(missing_ok=True)

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

        # TODO: don't delete things that are not ours
        # TODO: some of these don't exist any more?
        # for rmdir in ["sourceVersions", "papersToPrint", "media"]:
        #     shutil.rmtree(rmdir, ignore_errors=True)

        # surely Django will do this?  Else we need the settings here
        # Path("media").mkdir()

    def rebuild_migrations_and_migrate(self, engine):
        # print("Rebuild the database migrations and migrate")
        # for cmd in ["makemigrations", "migrate"]:
        # py_man_cmd = f"python3 manage.py {cmd}"
        # subprocess.check_call(split(py_man_cmd))

        call_command("makemigrations")
        call_command("migrate")

        if engine == "sqlite":
            database_service.sqlite_set_wal()

    def launch_huey_workers(self):
        # I don't understand why, but this seems to need to be run as a sub-proc
        # and not via call_command... maybe because it launches a bunch of background
        # stuff?

        print("Launching huey workers for background tasks")
        for cmd in ["djangohuey --quiet"]:  # quiet huey tasks.
            py_man_cmd = f"python3 manage.py {cmd}"
            return subprocess.Popen(split(py_man_cmd))

    def launch_server(self, *, port):
        print(f"Launching django server on localhost port {port}")
        # this needs to be run in the background
        cmd = f"python3 manage.py runserver {port}"
        return subprocess.Popen(split(cmd))

    def remove_old_migration_files(self):
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
        if engine == "postgres":
            # if database_services.is_there_a_postgres_db():
            #     print("Overwriting existing database")
            database_service.recreate_postgres_database()

        print("*" * 40)
        self.remove_old_migration_files()

        print("*" * 40)
        self.remove_old_db_and_misc_user_files(engine)

        print("*" * 40)
        self.rebuild_migrations_and_migrate(engine)
