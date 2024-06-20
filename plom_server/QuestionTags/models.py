# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models

class QuestionTag(models.Model):
    question_number = models.IntegerField()
    description = models.TextField()

    class Meta:
        db_table = 'questiontags_questiontag'

class Tag(models.Model):
    tag_name = models.TextField()
    description = models.TextField()