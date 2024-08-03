# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
from django.db import transaction
from django.contrib.auth.models import User
from Progress.services import UserInfoServices
from UserManagement.models import ProbationPeriod


class ProbationService:
    """Service for probationary period handling."""

    @transaction.atomic
    def new_limit_is_valid(self, limit: int, user: User) -> bool:
        """Check if the new limit is valid for the user.

        Current restriction:
        1. New limit must be non-negative.
        2. New limit must be greater or equal to the task claimed by the user.

        Args:
            limit: the new probation limit to be applied.
            user: user's username whose limit will be modified.

        Returns:
            True if the new limit can be applied to the user.
        """
        complete_and_claimed_tasks_dict = (
            UserInfoServices().get_total_annotated_and_claimed_count_based_on_user()
        )
        complete, claimed = complete_and_claimed_tasks_dict[user.username]

        if (limit >= 0) & (limit >= claimed):
            return True
        else:
            return False

    @transaction.atomic
    def can_set_probation(self, user: User) -> bool:
        """Check if a user (not in probation) can be set to probation.

        A user can't be set to probation, if they have claimed more questions than
        the default probation limit.

        Args:
            user: the user in query.

        Returns:
            True if the user can be set into probation, otherwise false.
        """
        complete_and_claim_dict = (
            UserInfoServices().get_total_annotated_and_claimed_count_based_on_user()
        )
        complete, claimed = complete_and_claim_dict[user.username]

        if claimed > ProbationPeriod.default_limit:
            return False
        else:
            return True
