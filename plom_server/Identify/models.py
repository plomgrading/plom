# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models
from django.contrib.auth.models import User

from Base.models import BaseTask, BaseAction
from Papers.models import Paper


class PaperIDTask(BaseTask):
    """Represents a test-paper that needs to be identified.

    paper: reference to Paper that needs to be IDed.
    latest_action: reference to PaperIDAction, the latest identification for the paper.
    priority: a float priority that provides the ordering for tasks presented for IDing,
        which is set to the inverse of the paper number by default.
    """

    def _determine_priority(self):
        return 1 / self.paper.paper_number

    def save(self, *args, **kwargs):
        if self.iding_priority is None:
            self.iding_priority = self._determine_priority()
        super().save(*args, **kwargs)

    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    latest_action = models.OneToOneField(
        "PaperIDAction", unique=True, null=True, on_delete=models.SET_NULL
    )
    iding_priority = models.FloatField(null=True, default=None)


class PaperIDAction(BaseAction):
    """Represents an identification of a test-paper."""

    is_valid = models.BooleanField(default=True)
    student_name = models.TextField(default="")
    student_id = models.TextField(default="")


class IDPrediction(models.Model):
    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    student_id = models.CharField(null=True, max_length=255)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    predictor = models.CharField(null=False, max_length=255)
    certainty = models.FloatField(null=False, default=0.0)
