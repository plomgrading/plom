# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models

class QuestionTag(models.Model):
    question_number = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return f"Q{self.question_number}: {self.description}"
