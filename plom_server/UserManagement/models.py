# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan

from django.db import models
from django.contrib.auth.models import User


class ProbationPeriod(models.Model):
    """Represents a probation period of a marker with its limit."""

    default_limit = 5
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limit = models.IntegerField(default=default_limit)

    def __str__(self):
        """Return a string representation of the probation period.

        Returns:
            str: A string describing the probation period and limit for the user.
        """
        return f"Probation Period for {self.user.username} with limit {self.limit}"

    @classmethod
    def set_default_limit(cls, new_limit: int) -> None:
        """Change default probation limit.

        Args:
            new_limit: the new probation limit.
        """
        cls.default_limit = new_limit
