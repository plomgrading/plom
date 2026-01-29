# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald

import shutil

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Removes old user-generated files, huey-process database, and misc."""

    def remove_misc_user_files(self):
        """Remove any user-generated files from django's MEDIA directory."""
        self.stdout.write(
            "Removing any user-generated files from django's MEDIA_ROOT directory"
        )
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def huey_cleanup(self):
        """Remove any existing huey db."""
        for path in settings.PLOM_BASE_DIR.glob("hueydb*.sqlite*"):
            self.stdout.write(f"Removing {path}")
            path.unlink(missing_ok=True)

    def handle(self, *args, **options):
        """Clean up, remove old DB and huey files, and rebuild db."""
        self.stdout.write("Removing old files, database, huey-db.")
        self.remove_misc_user_files()
        self.huey_cleanup()
        self.stdout.write("Note: neither server nor huey are running yet.")
        self.stdout.write("Note: no groups or users have been created yet.")
