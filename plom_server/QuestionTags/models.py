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
    tag_name = models.TextField()

    def __str__(self):
        """Return the tag name."""
        return str(self.tag_name)


class TmpAbstractQuestion(models.Model):
    question_index = models.IntegerField(default=0)
    tags = models.ManyToManyField(PedagogyTag)

    def __str__(self):
        """Return the question index."""
        return f"Question {str(self.question_index)}"


class QuestionTag(models.Model):
    question = models.ForeignKey(TmpAbstractQuestion, on_delete=models.CASCADE)
    tag = models.ForeignKey(PedagogyTag, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        """Return a string representation of the question-tag relationship."""
        user_id = self.user_id if self.user else "None"
        tag_name = self.tag.tag_name if self.tag else "None"
        return f"Question {self.question.id} tagged with '{tag_name}' by user {user_id}"
