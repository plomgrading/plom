# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Aden Chan
# Copyright (C) 2025 Colin B. Macdonald

from django.core.management.base import BaseCommand

from Finish.services import StudentMarkService


class Command(BaseCommand):
    """Get csv of student marks."""

    help = "Get csv of student marks."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        csv_as_string = StudentMarkService.build_marks_csv_as_string(True, True, True)
        with open("marks.csv", "w+") as fh:
            fh.write(csv_as_string)
