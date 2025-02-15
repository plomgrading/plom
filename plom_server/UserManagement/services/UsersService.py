# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024-2025 Aidan Murphy

from django.contrib.auth.models import User
from django.db import transaction


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
            they've already logged in;
            they've requested self-deletion.
    """
    user_to_delete = User.objects.get_by_natural_key(username)

    # prevent soft lock
    if user_to_delete.id == requester_id:
        raise ValueError("Users may not delete themselves.")

    if user_to_delete.is_superuser:
        raise ValueError(f"User: {username} is an admin and cannot be deleted.")

    # don't let users login in between checking and deletion
    with transaction.atomic():
        if user_to_delete.last_login:
            raise ValueError(
                f"User: {username} has at least 1 successful login,"
                "they can no longer be deleted."
            )

        deleted_username = user_to_delete.username
        user_to_delete.delete()

    return deleted_username
