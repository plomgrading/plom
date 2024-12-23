# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from Base.models import Tag

"""
Abstract model for associating multiple tags with a question index.

This model supports the many-to-many relationship between questions and tags.
It keeps track of multiple tags associated with a single question.
"""


class PedagogyTag(Tag):
    """Represents a tag with its description.
    
    Fields:
        tag_name (TextField): The name of the tag.
        description (TextField): The description of the tag.
        confidential_info (TextField): Private tag information not shown to students.
        help_threshold (FloatField): The score threshold at which help resources are shown in student report.
        help_resources (TextField): The help text to be shown in student report
    
    """

    tag_name = models.TextField(unique=True)
    description = models.TextField(
        null=True, blank=True, default=""
    )
    confidential_info = models.TextField(
        null=True, blank=True, default=""
    )
    help_threshold = models.FloatField(default=0.5)
    help_resources = models.TextField(
        null=True, blank=True, default=""
    )

    def __str__(self):
        """Return the tag name."""
        return str(self.tag_name)


class TmpAbstractQuestion(models.Model):
    """Represents the question index.

    This model exists to support the many-to-many relationship between questions and tags.
    It keeps track of multiple tags associated with a single question.
    """

    question_index = models.IntegerField(default=0)

    def __str__(self):
        """Return the question index."""
        return f"Question index {self.question_index}"


class QuestionTagLink(models.Model):
    """Represents a tag associated with a question by a user.

    This model links a specific pedagogy tag to a question and records the user who tagged the question
    as well as the time when the tag was added.

    Attributes:
        question (TmpAbstractQuestion): The question being tagged.
        tag (PedagogyTag): The pedagogy tag associated with the question.
        user (User): The user who tagged the question.
        time (DateTimeField): The time the tag was added.
    """

    question = models.ForeignKey(TmpAbstractQuestion, on_delete=models.CASCADE)
    tag = models.ForeignKey(PedagogyTag, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(default=timezone.now)

    class Meta:
        """Meta class for QuestionTagLink model.

        Defines the constraint for the QuestionTagLink model, ensuring
        that each combination of question, tag, and user is unique.
        """

        unique_together = ("question", "tag", "user")

    def __str__(self):
        """Returns a string representation of the question-tag relationship.

        The string includes the question id, tag name, and user id who tagged the question.
        """
        user_id = self.user_id if self.user else "None"
        tag_name = self.tag.tag_name if self.tag else "None"
        return f"Question {self.question.question_index} tagged with '{tag_name}' by user {user_id}"
