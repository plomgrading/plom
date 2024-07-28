# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
from django.db import transaction
from django.contrib.auth.models import User


class ProbationService:
    """Service for probationary period handling."""

    @transaction.atomic
    def new_limit_is_valid(self, limit: int, user: User) -> bool:
        """Check if the new limit is valid for the user.

        Current restriction: New limit must be non-negative.

        Args:
            limit: the new probationary limit to be applied.
            username: user's username whose limit will be modified.

        Returns:
            True if the new limit can be applied to the user.
        """

        if limit >= 0:
            return True
        else:
            return False
