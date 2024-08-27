# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Colin B. Macdonald

from django.db import models
from django.contrib.auth.models import User


class Quota(models.Model):
    """Represents a limitation on a user to mark only a certain number of questions."""

    default_limit = 12
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limit = models.IntegerField(default=default_limit)

    def __str__(self) -> str:
        """Return a string representation of the quota."""
        return f"Quota for {self.user.username} with limit {self.limit}"

    @classmethod
    def set_default_limit(cls, new_limit: int) -> None:
        """Change the default quota limit.

        Args:
            new_limit: the new quota limit.
        """
        cls.default_limit = new_limit
