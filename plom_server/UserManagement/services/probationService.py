# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
from django.db import transaction
from django.contrib.auth.models import User
from ..models import ProbationPeriod


class ProbationService:
    """Service for probationary period handling."""

    @transaction.atomic
    def new_limit_is_valid(self, limit: int, user: User) -> bool:
        """Check if the new limit is valid for the user.

        Current restriction: New limit must be non-negative and greater than
        current limit (if exists).

        Args:
            limit: the new probationary limit to be applied.
            username: user's username whose limit will be modified.

        Returns:
            True if the new limit can be applied to the user.
        """

        try:
            current_limit = ProbationPeriod.objects.get(user=user).limit
        except ProbationPeriod.DoesNotExist:
            current_limit = 0
        if limit >= current_limit:
            return True
        else:
            return False
