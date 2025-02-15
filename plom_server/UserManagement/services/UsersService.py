# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024-2025 Aidan Murphy

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction

from Progress.services import UserInfoServices
from Identify.services import IdentifyTaskService


# TODO: can probably do this in one call
def get_user_info() -> dict:
    users = {
        "managers": User.objects.filter(groups__name="manager"),
        "scanners": User.objects.filter(groups__name="scanner").exclude(
            groups__name="manager"
        ),
        "lead_markers": User.objects.filter(groups__name="lead_marker"),
        "markers": User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        ),
    }
    return users


def delete_user(username: str, requester_id: int | None = None) -> str:
    """Delete a user.

    Args:
        username: The username of the user to delete.
        requester_id: The db id of the user making this request.  This is
            optional: if `None` than fewer checks will be performed, for
            example this is used to prevent users from deleting themselves.

    Returns:
        The username of the deleted user.

    Raises:
        ObjectDoesNotExist: no such user.
        ValueError: user couldn't be deleted because: they're an admin;
            they're logged in; they've completed marking tasks;
            they've requested self-deletion.
    """
    user_to_delete = User.objects.get_by_natural_key(username)

    # prevent soft lock
    if user_to_delete.id == requester_id:
        raise ValueError("Users may not delete themselves.")

    if user_to_delete.is_superuser:
        raise ValueError(f"User: {username} is an admin and cannot be deleted.")

    online_user_ids = cache.get("online-now", [])
    # don't let users submit annotations in between checking and deletion
    with transaction.atomic():
        num_annotations, _ = (
            UserInfoServices().get_total_annotated_and_claimed_count_by_user(username)
        )
        if num_annotations > 0:
            # TODO: would be nice to have a unit test here
            raise ValueError(
                f"User: {username} has started marking, they cannot be deleted."
            )
        # TODO: should cascade and delete their IDing progress instead?
        if IdentifyTaskService().get_done_tasks(user_to_delete):
            raise ValueError(
                f"User: {username} has identified papers, they cannot be deleted."
            )

        if user_to_delete.id in online_user_ids:
            raise ValueError(
                f"User: {username} is currently logged in and cannot be deleted."
                "Hint: disabling a user will force a logout."
            )

        deleted_username = user_to_delete.username
        user_to_delete.delete()

    return deleted_username
