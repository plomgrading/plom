# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from django.db import models

from Base.models import BaseTask, BaseAction
from Papers.models import Paper


class PaperIDTask(BaseTask):
    """Represents a test-paper that needs to be identified."""

    paper = models.OneToOneField(Paper, on_delete=models.CASCADE)


class PaperIDAction(BaseAction):
    """Represents an identification of a test-paper."""

    student_name = models.TextField(default="")
    student_id = models.TextField(default="")
