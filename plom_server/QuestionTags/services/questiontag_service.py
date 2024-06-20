# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from Papers.services import SpecificationService
from QuestionTags.models import QuestionTag

def get_question_labels():
    """Return a list of tuples containing question number and question label."""
    question_labels = SpecificationService.get_question_labels()
    question_indices = SpecificationService.get_question_indices()
    return list(zip(question_indices, question_labels))

def add_question_tag(question_number, description):
    """Add a new question tag to the database."""
    QuestionTag.objects.create(question_number=question_number, description=description)