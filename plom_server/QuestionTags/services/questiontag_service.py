# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from QuestionTags.models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink
from django.db.utils import IntegrityError
from plom.tagging import is_valid_tag_text


class QuestionTagService:
    """Service class for managing question tags.

    This class provides methods to add, create, edit, and delete tags associated
    with questions, as well as to manage the links between questions and tags.
    """

    @staticmethod
    def add_question_tag_link(question_index, tag_names, user):
        """Add a question tag to the database.

        Args:
            question_index: The index of the question to be tagged.
            tag_names: A list of tag names to associate with the question.
            user: The user adding the tags.

        Returns:
            None on success or a string describing the error encountered.
        """
        question, created = TmpAbstractQuestion.objects.get_or_create(
            question_index=question_index
        )

        for tag_name in tag_names:
            if not is_valid_tag_text(tag_name):
                return f"Tag name '{tag_name}' contains invalid characters."

            try:
                tag, tag_created = PedagogyTag.objects.get_or_create(
                    tag_name=tag_name, defaults={"user": user}
                )
            except IntegrityError:
                tag = PedagogyTag.objects.get(tag_name=tag_name)

            try:
                QuestionTagLink.objects.get_or_create(
                    question=question, tag=tag, user=user
                )
            except IntegrityError:
                return f"Question {question_index} already tagged with '{tag_name}' by user {user.username}"

        question.save()

    @staticmethod
    def create_tag(tag_name, text, user):
        """Create a new tag.

        Args:
            tag_name: The short name of the tag we wish to create.
            text: The description of the tag.
            user: The user creating the tag.

        Returns:
            None on success or a string of an error message explaining that the tag already exists.
        """
        if not is_valid_tag_text(tag_name):
            return f"Tag name '{tag_name}' contains invalid characters."

        try:
            PedagogyTag.objects.create(tag_name=tag_name, text=text, user=user)
            return None
        except IntegrityError:
            return f"A tag with the name '{tag_name}' already exists."

    @staticmethod
    def delete_tag(tag_id):
        """Delete a tag.

        Args:
            tag_id: The ID of the tag to delete.

        Returns:
            None on success or a string describing the error encountered.
        """
        tag = PedagogyTag.objects.filter(id=tag_id).first()
        if not tag:
            return "Tag not found."

        try:
            tag.delete()
            return None
        except Exception as e:
            return str(e)

    @staticmethod
    def edit_tag(tag_id, tag_name, text):
        """Edit an existing tag.

        Args:
            tag_id: The ID of the tag to edit.
            tag_name: The new name of the tag.
            text: The new description of the tag.

        Returns:
            None on success or a string describing the error encountered.
        """
        if not is_valid_tag_text(tag_name):
            return f"Tag name '{tag_name}' contains invalid characters."

        tag = PedagogyTag.objects.filter(id=tag_id).first()
        if not tag:
            return "Tag not found."

        if PedagogyTag.objects.filter(tag_name=tag_name).exclude(id=tag_id).exists():
            return f"A tag with the name '{tag_name}' already exists."

        try:
            tag.tag_name = tag_name
            tag.text = text
            tag.save()
            return None
        except Exception as e:
            return str(e)

    @staticmethod
    def delete_question_tag_link(question_tag_id):
        """Delete a question-tag link.

        Args:
            question_tag_id: The ID of the question-tag link to delete.

        Returns:
            None on success or a string describing the error encountered.
        """
        question_tag = QuestionTagLink.objects.filter(id=question_tag_id).first()
        if not question_tag:
            return "Question tag link not found."

        try:
            question_tag.delete()
            return None
        except Exception as e:
            return str(e)
