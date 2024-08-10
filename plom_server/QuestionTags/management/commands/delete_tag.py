# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import QuestionTagService
from ...models import PedagogyTag


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
        try:
            QuestionTagService.delete_tag(tag.pk)
        except ValueError as err:
            raise CommandError(f"Error deleting tag: {err}")
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted tag "{tag_name}"')
            )
