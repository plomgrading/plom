# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from django.db import transaction
from django.contrib.auth.models import User

from Progress.services import UserInfoServices
from ..models import Quota


@transaction.atomic
def is_proposed_limit_valid(limit: int, user: User) -> bool:
    """Check if the proposed limit would valid for the user.

    Current restriction:
    1. New limit must be non-negative.
    2. New limit must be greater or equal to the task claimed by the user.

    Args:
        limit: the new quota limit to be applied.
        user: user's username whose limit will be modified.

    Returns:
        True if the new limit can be applied to the user.
    """
    complete, claimed = UserInfoServices.get_total_annotated_and_claimed_count_by_user(
        user.username
    )

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
    complete, claimed = UserInfoServices.get_total_annotated_and_claimed_count_by_user(
        user.username
    )

    if complete > Quota.default_limit:
        return False
    else:
        return True


def get_list_of_usernames_with_quotas() -> list[str]:
    return Quota.objects.values_list("user__username", flat=True)


def get_list_of_user_pks_with_quotas() -> list[int]:
    return Quota.objects.values_list("user_id", flat=True)
