# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.db import models
from django.contrib.auth.models import User
from Mark.models import MarkingTask


class AnnotationImage(models.Model):
    """A raster representation of an annotated question."""

    path = models.TextField(null=False, default="")
    hash = models.TextField(null=False, default="")


class Annotation(models.Model):
    """Represents a marker's annotation of a particular test paper's question."""
    edition = models.IntegerField(null=True)
    score = models.IntegerField(null=True)
    image = models.OneToOneField(AnnotationImage, on_delete=models.CASCADE)
    annotation_data = models.JSONField(null=True)
    marking_time = models.PositiveIntegerField(null=True)
    task = models.ForeignKey(MarkingTask, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
