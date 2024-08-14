# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations
from typing import Dict, List

from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.db import transaction

from plom.tagging import is_valid_tag_text
from ..models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink


class QuestionTagService:
    """Service class for managing question tags.

    This class provides methods to add, create, edit, and delete tags associated
    with questions, as well as to manage the links between questions and tags.
    """

    @staticmethod
    def add_question_tag_link(
        question_index: int, tag_names: list[str], user_obj: User
    ) -> None:
        """Add a question tag to the database.

        Args:
            question_index: The index of the question to be tagged.
            tag_names: A list of tag names to associate with the question.
            user_obj: The user adding the tags.

        Raises:
            ValueError: when tag_name contains invalid characters.
            IntegrityError: when question is already tagged with that tag.
        """
        question, created = TmpAbstractQuestion.objects.get_or_create(
            question_index=question_index
        )

        for tag_name in tag_names:
            if not is_valid_tag_text(tag_name):
                raise ValueError(f"Tag name '{tag_name}' contains invalid characters.")

            try:
                tag, tag_created = PedagogyTag.objects.get_or_create(
                    tag_name=tag_name, defaults={"user": user_obj}
                )
            except IntegrityError:
                tag = PedagogyTag.objects.get(tag_name=tag_name)

            try:
                QuestionTagLink.objects.get_or_create(
                    question=question, tag=tag, user=user_obj
                )
            except IntegrityError:
                raise IntegrityError(
                    f"Question {question_index} already tagged with '{tag_name}' by user {user_obj.username}"
                )

        question.save()

    @staticmethod
    def create_tag(
        tag_name: str, text: str, *, user: User, confidential_info: str | None = None
    ) -> None:
        """Create a new tag.

        Args:
            tag_name: The short name of the tag we wish to create.
            text: The description of the tag.

        Keyword Args:
            user: The user creating the tag.
            confidential_info: Text shown only to markers, not the students.

        Raises:
            ValueError: when the tag name contains invalid character.
            IntegrityError: when a tag with that name already exists.
        """
        if not is_valid_tag_text(tag_name):
            raise ValueError(f"Tag name '{tag_name}' contains invalid characters.")

        try:
            PedagogyTag.objects.create(
                tag_name=tag_name,
                text=text,
                user=user,
                confidential_info=confidential_info,
            )
        except IntegrityError:
            raise IntegrityError(f"A tag with the name '{tag_name}' already exists.")

    @staticmethod
    def delete_tag(tag_pk: int) -> None:
        """Delete a questin-tag.

        Args:
            tag_pk: The PK of the tag to delete.

        Raises:
            ValueError: if question-tag with that pk does not exist.
        """
        try:
            tag = PedagogyTag.objects.get(pk=tag_pk)
        except PedagogyTag.DoesNotExist:
            raise ValueError(f"Cannot find tag with pk = {tag_pk}")

        tag.delete()

    @staticmethod
    def edit_tag(tag_pk, tag_name, text, *, confidential_info=None):
        """Edit an existing tag.

        Args:
            tag_pk: The pk of the tag to edit.
            tag_name: The new name of the tag.
            text: The new description of the tag.

        Keyword Args:
            confidential_info: text shown only to markers, not the students.

        Raises:
            ValueError: if the tag name contains invalid characters,
                or no tag with given pk exists.
            IntegrityError: if a tag with the new name already exists.


        """
        if not is_valid_tag_text(tag_name):
            raise ValueError(f"Tag name '{tag_name}' contains invalid characters.")

        if PedagogyTag.objects.filter(tag_name=tag_name).exclude(pk=tag_pk).exists():
            raise IntegrityError(f"A tag with the name '{tag_name}' already exists.")

        with transaction.atomic():
            try:
                tag = PedagogyTag.objects.select_for_update().get(pk=tag_pk)
            except PedagogyTag.DoesNotExist:
                raise ValueError(f"Tag with pk '{tag_pk}' does not exist.")

            tag.tag_name = tag_name
            tag.text = text
            tag.confidential_info = confidential_info
            tag.save()

    @staticmethod
    def delete_question_tag_link(question_tag_pk):
        """Delete a question-tag link.

        Args:
            question_tag_pk: The pk of the question-tag link to delete.

        Raises:
            ValueError: if no question-tag-link with that pk exists.
        """
        try:
            question_tag = QuestionTagLink.objects.get(pk=question_tag_pk)
        except QuestionTagLink.DoesNotExist:
            raise ValueError("Question tag link not found.")

        question_tag.delete()

    @staticmethod
    def are_there_question_tag_links() -> bool:
        """True if any pedagogy-tags have been linked to questions."""
        return QuestionTagLink.objects.exists()

    @staticmethod
    def get_tag_to_question_links() -> Dict[str, List[int]]:
        """Get a dictionary of pedagogy-tags and their linked questions.

        Returns:
            A dict of {tag_name: [list of question-indices]}
        """
        tag_to_question_list: Dict[str, List[int]] = {}
        for qtl in QuestionTagLink.objects.all().prefetch_related("question", "tag"):
            # want a dict of (key, list[])
            tag_to_question_list.setdefault(qtl.tag.tag_name, [])
            tag_to_question_list[qtl.tag.tag_name].append(qtl.question.question_index)
        return tag_to_question_list

    @staticmethod
    def get_pedagogy_tag_descriptions() -> Dict[str, str]:
        """Return a dict of {tag_name: tag_description}."""
        return {ptag.tag_name: ptag.text for ptag in PedagogyTag.objects.all()}
