# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.db import models
from django.contrib.auth.models import User


class Tag(models.Model):
    """Represents a tag assigned to papers."""
