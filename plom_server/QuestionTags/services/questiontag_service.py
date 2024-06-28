# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from QuestionTags.models import QuestionTag, PedagogyTag
from django.shortcuts import get_object_or_404


class QuestionTagService:
    @staticmethod
    def add_question_tag(question_index, tag_names, user):
        """Add a question tag to the database."""
        question_tag = QuestionTag.objects.create(question_index=question_index)
        for tag_name in tag_names:
            tag, created = PedagogyTag.objects.get_or_create(
                tag_name=tag_name, defaults={"user": user}
            )
            if created:
                tag.user = user
                tag.save()
            question_tag.tags.add(tag)
        question_tag.save()

    @staticmethod
    def create_tag(tag_name, text, user):
        """Create a new tag."""
        PedagogyTag.objects.create(tag_name=tag_name, text=text, user=user)

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
