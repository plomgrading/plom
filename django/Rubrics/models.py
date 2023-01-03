# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.db import models


class Rubric(models.Model):
    """
    Represents a marker's comment and mark delta for a particular question.
    """

    key = models.TextField(unique=True, null=False)  # system generated + short
    kind = models.TextField(
        null=False, default="abs"
    )  # abs, neut, delt, relative - is short
    delta = models.TextField(null=False, default="0")  # is short
    text = models.TextField(null=False, default="")  # can be long
    question = models.IntegerField(null=False, default=0)
