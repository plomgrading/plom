# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from ...services import QuestionTagService


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
        parser.add_argument(
            "username", type=str, help="The username of the user creating the tag"
        )

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        tag_name = kwargs["tag_name"]
        description = kwargs["description"]
        confidential_info = kwargs.get("confidential_info", "")
        username = kwargs["username"]

        # Fetch the user object based on the username
        User = get_user_model()
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        # Use the create_tag method from QuestionTagService to create the tag
        try:
            QuestionTagService.create_tag(
                tag_name=tag_name,
                description=description,
                user=user_obj,
                confidential_info=confidential_info,
            )
        except (ValueError, IntegrityError) as err:
            raise CommandError(f"Error creating tag: {err}")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created tag "{tag_name}" by {username}'
                )
            )
