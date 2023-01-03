# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import random

from django.db import models
from django.contrib.auth.models import User


def generate_key():
    return "".join([str(random.randint(0, 9)) for i in range(12)])


def generate_unique_key():
    key = generate_key()
    existing_keys = Rubric.objects.all().values_list("key", flat=True)
    while key in existing_keys:
        key = generate_key()
    return key


class Rubric(models.Model):
    """
    Represents a marker's comment and mark delta for a particular question.
    """

    key = models.TextField(null=False, default=generate_unique_key)
    kind = models.TextField(
        null=False, default="abs"
    )  # abs, neut, delt, relative - is short
    delta = models.TextField(null=False, default="0")  # is short
    text = models.TextField(null=False, default="")  # can be long
    question = models.IntegerField(null=False, default=0)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    tags = models.TextField(null=True)  # can be long
    meta = models.TextField(null=True)  # can be long
