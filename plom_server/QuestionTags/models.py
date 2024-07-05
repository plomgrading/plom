# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models
from Base.models import Tag
from django.contrib.auth.models import User
from django.utils import timezone

""" This presents the abstract notion of a question, which are otherwise
    just integers of their question index. It exists mainly to support
    the ManyToManyField contained in it.
    TODO: it might be renamed or replaced some day
"""


class PedagogyTag(Tag):
    """Represents a tag with its description."""

    tag_name = models.TextField(unique=True)

    def __str__(self):
        """Return the tag name."""
        return str(self.tag_name)


class TmpAbstractQuestion(models.Model):
    """Represents an abstract question with an index."""

    question_index = models.IntegerField(default=0)

    def __str__(self):
        """Return the question index."""
        return f"Question index {str(self.question_index)}"


class QuestionTagLink(models.Model):
    """Represents a tag associated with a question by a user.

    question: The question being tagged.
    tag: The pedagogy tag associated with the question.
    user: The user who tagged the question.
    time: The time the tag was added.
    """

    question = models.ForeignKey(TmpAbstractQuestion, on_delete=models.CASCADE)
    tag = models.ForeignKey(PedagogyTag, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("question", "tag", "user")

    def __str__(self):
        """
        Returns a string representation of the question-tag relationship.

        The string shows the question index, tag name, and user id who tagged the question.
        """
        user_id = self.user_id if self.user else "None"
        tag_name = self.tag.tag_name if self.tag else "None"
        return f"Question {self.question.id} tagged with '{tag_name}' by user {user_id}"
