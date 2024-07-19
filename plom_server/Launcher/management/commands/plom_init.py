# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    """Initialize a plom server for production.

    Removes old DB, user-generated files and huey queue.
    Then creates a new database and tables, user groups, and
    admin and manager users.
    """

    def handle(self, *args, **options):
        call_command("plom_clean_all_and_build_db")
        call_command("plom_make_groups_and_first_users")
