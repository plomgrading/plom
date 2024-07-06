# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from QuestionTags.models import TmpAbstractQuestion, PedagogyTag, QuestionTagLink
from django.shortcuts import get_object_or_404
from django.db.utils import IntegrityError


class QuestionTagService:
    @staticmethod
    def add_question_tag(question_index, tag_names, user):
        """Add a question tag to the database."""
        question, created = TmpAbstractQuestion.objects.get_or_create(
            question_index=question_index
        )
        for tag_name in tag_names:
            try:
                tag, tag_created = PedagogyTag.objects.get_or_create(
                    tag_name=tag_name, defaults={"user": user}
                )
                question_tag, qt_created = QuestionTagLink.objects.get_or_create(
                    question=question, tag=tag, user=user
                )
            except IntegrityError:
                # Handle the case where the tag_name already exists in a race condition
                tag = PedagogyTag.objects.get(tag_name=tag_name)
                question_tag, qt_created = QuestionTagLink.objects.get_or_create(
                    question=question, tag=tag, user=user
                )
        question.save()

    @staticmethod
    def create_tag(tag_name, text, user):
        """Create a new tag."""
        try:
            PedagogyTag.objects.create(tag_name=tag_name, text=text, user=user)
            return None
        except IntegrityError:
            return f"A tag with the name '{tag_name}' already exists."

    @staticmethod
    def delete_tag(tag_id):
        """Delete a tag."""
        tag = get_object_or_404(PedagogyTag, id=tag_id)
        tag.delete()

    @staticmethod
    def edit_tag(tag_id, tag_name, text):
        """Edit an existing tag."""
        tag = get_object_or_404(PedagogyTag, id=tag_id)
        tag.tag_name = tag_name
        tag.text = text
        tag.save()

    @staticmethod
    def delete_question_tag(question_tag_id):
        """Delete a question-tag link."""
        question_tag = get_object_or_404(QuestionTagLink, id=question_tag_id)
        question_tag.delete()
