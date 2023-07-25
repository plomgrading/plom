# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from Tags.services import TagService


class Command(BaseCommand):
    """Command tool for clustering and tagging questions.

    Currently only does clustering on student id digits and tags the first question.

    python3 manage.py cluster_and_tag
    """

    help = """Add a tag to a specific paper."""

    def get_digits(self):
        """Get all the digits from the database."""
        pass

    def cluster_digits(self):
        """Cluster the digits."""
        pass

    def tag_question(self):
        """Tag the first question."""
        pass

    def add_arguments(self, parser):
        parser.add_argument(
            "digit_index", type=int, help="Digit index to cluster on, range: [0-7]"
        )

    def handle(self, *args, **options):
        pass
