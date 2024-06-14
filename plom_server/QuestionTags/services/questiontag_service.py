# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from Papers.services import SpecificationService

def get_question_labels():
    """Return a list of tuples containing question number and question label."""
    question_labels = SpecificationService.get_question_labels()
    question_indices = SpecificationService.get_question_indices()
    return list(zip(question_indices, question_labels))
