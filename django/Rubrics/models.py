# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

import random

from django.db import models
from django.contrib.auth.models import User
from polymorphic.models import PolymorphicModel


def generate_key():
    return "".join([str(random.randint(0, 9)) for i in range(12)])


def generate_unique_key():
    key = generate_key()
    existing_keys = Rubric.objects.all().values_list("key", flat=True)
    while key in existing_keys:
        key = generate_key()
    return key


class Rubric(PolymorphicModel):
    """
    Represents a marker's comment and mark delta for a particular question.
    """

    key = models.TextField(null=False, default=generate_unique_key)
    text = models.TextField(null=False, default="")  # can be long
    question = models.IntegerField(null=False, default=0)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    tags = models.TextField(null=True)  # can be long
    meta = models.TextField(null=True)  # can be long


class RelativeRubric(Rubric):
    """
    A rubric that modifies the total score by an integer value.
    """

    delta = models.TextField(null=False, default="0")  # is short


class RubricPane(models.Model):
    """
    A user's configuration for the 'rubrics' pane in the annotation window.
    """

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    data = models.JSONField(null=False, default=dict)
