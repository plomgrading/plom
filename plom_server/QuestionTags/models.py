# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models
from Base.models import Tag

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
