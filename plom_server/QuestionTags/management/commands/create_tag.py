# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
from django.core.management.base import BaseCommand, CommandError
from QuestionTags.models import PedagogyTag


class Command(BaseCommand):
    """Management command to create a new tag."""

    help = "Create a new tag"

    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument("tag_name", type=str, help="The name of the tag")
        parser.add_argument("description", type=str, help="The description of the tag")
        parser.add_argument(
            "--confidential_info",
            type=str,
            help="The confidential_info of the tag",
            default="",
        )

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        tag_name = kwargs["tag_name"]
        description = kwargs["description"]
        confidential_info = kwargs.get("confidential_info", "")

        try:
            tag, created = PedagogyTag.objects.get_or_create(
                tag_name=tag_name,
                defaults={"text": description, "confidential_info": confidential_info},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created tag "{tag_name}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tag "{tag_name}" already exists')
                )
        except Exception as e:
            raise CommandError(f"Error creating tag: {e}")
