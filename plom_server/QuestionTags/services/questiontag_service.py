# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from Papers.services import SpecificationService
from QuestionTags.models import QuestionTag, Tag
from django.shortcuts import get_object_or_404


class QuestionTagService:
    @staticmethod
    def get_question_labels():
        """Return a list of tuples containing question index and question label."""
        question_labels = SpecificationService.get_question_labels()
        question_indices = SpecificationService.get_question_indices()
        return list(zip(question_indices, question_labels))

    @staticmethod
    def add_question_tag(question_index, tag_names, description):
        """Add a question tag to the database."""
        question_tag = QuestionTag.objects.create(
            question_index=question_index, description=description
        )
        for tag_name in tag_names:
            tag = Tag.objects.get(tag_name=tag_name)
            question_tag.tags.add(tag)
        question_tag.save()

    @staticmethod
    def create_tag(tag_name, description):
        """Create a new tag."""
        Tag.objects.create(tag_name=tag_name, description=description)

    @staticmethod
    def delete_tag(tag_id):
        """Delete a tag."""
        tag = get_object_or_404(Tag, id=tag_id)
        tag.delete()

    @staticmethod
    def edit_tag(tag_id, tag_name, tag_description):
        """Edit an existing tag."""
        tag = get_object_or_404(Tag, id=tag_id)
        tag.tag_name = tag_name
        tag.description = tag_description
        tag.save()
