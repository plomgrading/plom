# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy

from django.db import transaction
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from plom_server.Progress.services import UserInfoService
from ..models import Quota


@transaction.atomic
def can_set_quota(user: User, limit: int | None = None) -> bool:
    """Check if a user can be set to a particular quota.

    A user can't be restricted to fewer questions than they've already marked.

    Args:
        user: the user to query.

    Keyword Args:
        limit: the limit to check for the user, if omitted
            or `None` then defaults to the current default
            quota limit.

    Returns:
        True if the user can be set to the quota, otherwise false.
    """
    complete, claimed = UserInfoService.get_total_annotated_and_claimed_count_by_user(
        user.username
    )
    if limit is None:
        limit = Quota.default_limit

    if complete > limit or limit < 0:
        return False
    else:
        return True


def get_list_of_usernames_with_quotas() -> list[str]:
    return Quota.objects.values_list("user__username", flat=True)


def get_list_of_user_pks_with_quotas() -> list[int]:
    return Quota.objects.values_list("user_id", flat=True)


@transaction.atomic
def set_quotas_for_userlist(
    user_ids: list[str], new_limit: int
) -> tuple[list[str], list[str]]:
    """Set quotas for multiple users.

    If a user's limit can't be successfully updated, they will be skipped.

    Args:
        user_ids: a list of user ids.
        new_limit: the new task limit for the users in `user_ids`.

    Returns:
        Two lists of usernames - the first is the list of users updated
        successfully, the second is a list of users who couldn't be updated.
    """
    valid_markers = []
    invalid_markers = []
    for user_id in user_ids:
        user = get_object_or_404(User, pk=user_id)
        quota = Quota.objects.get(user=user)
        if not can_set_quota(user=user, limit=new_limit):
            invalid_markers.append(user.username)
        else:
            valid_markers.append(user.username)
            quota.limit = new_limit
            quota.save()

    return valid_markers, invalid_markers
