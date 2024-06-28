# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models
from Base.models import Tag


class PedagogyTag(Tag):
    tag_name = models.TextField()

    def __str__(self):
        """Return the tag name."""
        return str(self.tag_name)


class QuestionTag(models.Model):
    question_index = models.IntegerField(default=0)
    tags = models.ManyToManyField(PedagogyTag)
