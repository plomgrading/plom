# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from ...services import QuestionTagService


class Command(BaseCommand):
    """Management command to upload tags from a csv."""

    help = "Upload question-tags from a csv file."

    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument(
            "filename", type=str, help="The name csv containing the tags"
        )
        parser.add_argument(
            "username", type=str, help="The username of the user creating the tag"
        )

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        filename = kwargs.get("filename")
        username = kwargs["username"]

        # Fetch the user object based on the username
        User = get_user_model()
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        filepath = Path(filename)
        if not filepath.exists():
            raise CommandError(f"Cannot open file {filepath}")
        if filepath.suffix.casefold() != ".csv":
            raise CommandError(f"Cannot open file {filepath} --- must be a csv file")

        required_cols = ["Name", "Description", "Confidential_Info"]
        with filepath.open("r") as fh:
            red = csv.DictReader(fh)
            cols_present = red.fieldnames
            if any(req not in cols_present for req in required_cols):
                raise CommandError("CSV file does not have required column headings")

            for row in red:
                try:
                    QuestionTagService.create_tag(
                        tag_name=row["Name"],
                        text=row["Description"],
                        user=user_obj,
                        confidential_info=row["Confidential_Info"],
                    )
                except (ValueError, IntegrityError) as err:
                    raise CommandError(f"Error creating tag: {err}")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully created tag \"{row['Name']}\" by {username}"
                        )
                    )
