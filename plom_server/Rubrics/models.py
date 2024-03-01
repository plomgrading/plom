# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

import random

from django.db import models
from django.contrib.auth.models import User
from Mark.models.annotations import Annotation


def generate_key():
    return "".join([str(random.randint(0, 9)) for i in range(12)])


def generate_unique_key():
    key = generate_key()
    existing_keys = Rubric.objects.all().values_list("key", flat=True)
    while key in existing_keys:
        key = generate_key()
    return key


class Rubric(models.Model):
    """Represents a marker's comment and mark delta for a particular question."""

    key = models.TextField(null=False, default=generate_unique_key)
    kind = models.TextField(null=False)
    display_delta = models.TextField(null=False, default="")  # is short
    value = models.IntegerField(null=False, default=0)
    out_of = models.IntegerField(null=False, default=0)
    text = models.TextField(null=False)  # can be long
    question = models.IntegerField(null=False, default=0)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    tags = models.TextField(null=True, default="")  # can be long
    meta = models.TextField(null=True, blank=True, default="")  # can be long
    versions = models.JSONField(null=True, default=list)
    parameters = models.JSONField(null=True, default=list)
    annotations = models.ManyToManyField(Annotation, blank=True)
    system_rubric = models.BooleanField(null=False, default=False)
    published = models.BooleanField(null=False, default=True)


class RubricPane(models.Model):
    """A user's configuration for the 'rubrics' pane in the annotation window."""

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    question = models.PositiveIntegerField(default=0)
    data = models.JSONField(null=False, default=dict)
