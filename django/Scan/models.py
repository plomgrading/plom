# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class StagingBundle(models.Model):
    """
    A user-uploaded bundle that isn't validated.
    """

    slug = models.TextField(default="", unique=True)
    file_path = models.TextField(default="")
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time_uploaded = models.DateField(default=timezone.now, blank=True)
    pdf_hash = models.CharField(null=False, max_length=64)
