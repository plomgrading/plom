# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

from plom_server.Papers.services import SpecificationService
from plom_server.Papers.models.specifications import SpecQuestion
from ...services import QuestionTagService
from ...models import PedagogyTag


class Command(BaseCommand):
    """Management command to link a tag with a question."""

    help = "Link a tag with a question"

    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument(
            "question_index", type=int, help="The index of the question"
        )
        parser.add_argument("tag_name", type=str, help="The name of the tag to link")
        parser.add_argument(
            "username", type=str, help="The username of the user linking the tag"
        )

    def handle(self, *args, **kwargs):
        """Handle the command execution."""
        question_index = kwargs["question_index"]
        tag_name = kwargs["tag_name"]
        username = kwargs["username"]

        # Fetch the user object based on the username
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        # Validate the question index using SpecificationService
        try:
            SpecificationService.get_question_label(question_index)
        except SpecQuestion.DoesNotExist:
            raise CommandError(
                f"Question with index '{question_index}' does not exist. Cannot create link."
            )

        # Ensure the tag exists in the database
        try:
            PedagogyTag.objects.get(tag_name=tag_name)
        except PedagogyTag.DoesNotExist:
            raise CommandError(f"Tag '{tag_name}' does not exist. Cannot create link.")

        # Use the add_question_tag_link method from QuestionTagService
        try:
            QuestionTagService.add_question_tag_link(
                question_index=question_index,
                tag_names=[tag_name],
                user_obj=user,  # Changed 'user' to 'user_obj'
            )
        except (IntegrityError, ValueError) as err:
            raise CommandError(f"Error adding tag: {err}")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully linked tag "{tag_name}" with question {question_index} by {username}'
                )
            )
