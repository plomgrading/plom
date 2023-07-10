# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models

from Base.models import BaseTask, Tag
from Papers.models import Paper


class MarkingTask(BaseTask):
    """Represents a single question that needs to be marked.

    paper: reference to Paper, the test-paper of the question
    code: str, a unique string for indexing a marking task
    question_number: int, the question to mark
    question_version: int, the version of the question
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    code = models.TextField(default="", unique=False)
    question_number = models.PositiveIntegerField(null=False, default=0)
    question_version = models.PositiveIntegerField(null=False, default=0)
    latest_annotation = models.OneToOneField(
        "Annotation", unique=True, null=True, on_delete=models.SET_NULL
    )
    marking_priority = models.FloatField(null=False, default=1.0)


class MarkingTaskTag(Tag):
    """Represents a tag that can be assigned to one or more marking tasks."""

    task = models.ManyToManyField(MarkingTask)
