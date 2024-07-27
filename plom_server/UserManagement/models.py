# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models
from django.contrib.auth.models import User


class ProbationPeriod(models.Model):
    """Represents a probation period of a marker with its limit."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limit = models.IntegerField(default=5)

    def __str__(self):
        """Return a string representation of the probation period.

        Returns:
            str: A string describing the probation period and limit for the user.
        """
        return f"Probation Period for {self.user.username} with limit {self.limit}"
