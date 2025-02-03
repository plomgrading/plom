# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.management.base import BaseCommand

from ...services import TaMarkingService


class Command(BaseCommand):
    """Get csv of TA marking information."""

    help = "Get csv of TA marking information."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        csv_as_string = TaMarkingService().build_ta_info_csv_as_string()
        with open("ta_info.csv", "w+") as fh:
            fh.write(csv_as_string)
