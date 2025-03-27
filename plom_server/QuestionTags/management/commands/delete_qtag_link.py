# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from plom_server.Papers.services import SpecificationService
from plom_server.Papers.models.specifications import SpecQuestion
from ...services import QuestionTagService
from ...models import PedagogyTag, QuestionTagLink


class Command(BaseCommand):
    """Management command to delete a specific link between a question and a tag."""

    help = "Delete a specific link between a question and a tag"

    def add_arguments(self, parser):
        """Define arguments for the management command."""
        parser.add_argument(
            "question_index", type=int, help="The index of the question"
        )
        parser.add_argument("tag_name", type=str, help="The name of the tag to unlink")
        parser.add_argument(
            "username",
            type=str,
            help="The username of the user performing the deletion",
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
                f"Question with index '{question_index}' does not exist."
            )

        # Ensure the tag exists in the database
        try:
            tag = PedagogyTag.objects.get(tag_name=tag_name)
        except PedagogyTag.DoesNotExist:
            raise CommandError(f"Tag '{tag_name}' does not exist.")

        # Fetch and validate the question-tag link
        try:
            question_tag_link = QuestionTagLink.objects.get(
                question__question_index=question_index, tag=tag, user=user
            )
        except QuestionTagLink.DoesNotExist:
            raise CommandError(
                f"Link between question '{question_index}' and tag '{tag_name}' does not exist or you do not have permission to delete it."
            )

        # Use the delete_question_tag_link method from QuestionTagService
        error_message = QuestionTagService.delete_question_tag_link(
            question_tag_link.id
        )

        if error_message:
            raise CommandError(f"Error deleting link: {error_message}")
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted link between question "{question_index}" and tag "{tag_name}" by user "{username}"'
                )
            )
