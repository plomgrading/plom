# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald

from django.db import transaction
from django.contrib.auth.models import User

from Progress.services import UserInfoServices
from ..models import Quota


@transaction.atomic
def new_limit_is_valid(limit: int, user: User) -> bool:
    """Check if the new limit is valid for the user.

    Current restriction:
    1. New limit must be non-negative.
    2. New limit must be greater or equal to the task claimed by the user.

    Args:
        limit: the new quota limit to be applied.
        user: user's username whose limit will be modified.

    Returns:
        True if the new limit can be applied to the user.
    """
    complete_and_claimed_tasks_dict = (
        UserInfoServices.get_total_annotated_and_claimed_count_by_user()
    )
    complete, claimed = complete_and_claimed_tasks_dict[user.username]

    if (limit >= 0) & (limit >= complete):
        return True
    else:
        return False


@transaction.atomic
def can_set_quota(user: User) -> bool:
    """Check if a user (not currently with a quota) can be set to a quota.

    A user can't be quota limited, if they have marked more questions than
    the default quota limit.

    Args:
        user: the user in query.

    Returns:
        True if the user can be set to quota limited, otherwise false.
    """
    complete_and_claim_dict = (
        UserInfoServices.get_total_annotated_and_claimed_count_by_user()
    )
    complete, claimed = complete_and_claim_dict[user.username]

    if complete > Quota.default_limit:
        return False
    else:
        return True
