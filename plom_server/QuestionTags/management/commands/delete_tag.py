# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.core.management.base import BaseCommand, CommandError
from QuestionTags.services import QuestionTagService
from QuestionTags.models import PedagogyTag


class Command(BaseCommand):
    """Management command to delete an existing tag."""

    help = "Delete an existing tag"

    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument("tag_name", type=str, help="The name of the tag to delete")

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        tag_name = kwargs["tag_name"]

        # Fetch the tag based on the tag_name
        try:
            tag = PedagogyTag.objects.get(tag_name=tag_name)
        except PedagogyTag.DoesNotExist:
            raise CommandError(f'Tag "{tag_name}" does not exist')

        # Use the delete_tag method from QuestionTagService to delete the tag
        error_message = QuestionTagService.delete_tag(tag.id)

        if error_message:
            raise CommandError(f"Error deleting tag: {error_message}")
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted tag "{tag_name}"')
            )
