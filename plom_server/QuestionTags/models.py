# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models


class Tag(models.Model):
    tag_name = models.TextField()
    description = models.TextField()


class QuestionTag(models.Model):
    question_index = models.IntegerField(default=0)
    description = models.TextField()
    tags = models.ManyToManyField(Tag)
