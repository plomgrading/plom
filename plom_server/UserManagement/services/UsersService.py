# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2026 Aidan Murphy
# Copyright (C) 2025 Bryan Tanady

from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.forms.models import model_to_dict


def get_user_info() -> dict:
    # TODO: can probably do this in one call
    # all_users = User.objects.all().prefetch_related("auth_token")
    # for x in all_users:
    users = {
        "managers": User.objects.filter(groups__name="manager"),
        "scanners": User.objects.filter(groups__name="scanner"),
        "lead_markers": User.objects.filter(groups__name="lead_marker"),
        "markers": User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        ),
        "identifiers": User.objects.filter(groups__name="identifier"),
    }
    return users


def get_list_of_user_info() -> list[dict[str, Any]]:
    """Get a list of info about Users.

    Returns:
        A list of dicts, one dict for each user. Each dict has three
        keys: "user", "groups", and "signed_in_to_client". The "user"
        key returns a dict equivalent of the User obj, *not including
        @property fields* like "auth_token" or "has_usable_password".
    """
    user_list = []
    for user in User.objects.all():
        # auth_token is a computed attribute on the model
        # it is also sensitive, so don't place in user_dict
        try:
            user.auth_token  # throws exception if it doesn't exist
            has_auth_token = True
        except ObjectDoesNotExist:
            has_auth_token = False

        user_list.append(
            {
                "user": model_to_dict(user),
                "groups": ", ".join(user.groups.values_list("name", flat=True)),
                "signed_in_to_client": has_auth_token,
            }
        )
    return user_list


def get_user_info_list_of_dicts() -> list[dict[str, Any]]:
    """Get a list of info about Users, appropriate to the outside, such as the client.

    Returns:
        A list of dicts, one dict for each user. Each dict has keys "uid"
        "username", name", and "groups".  More might be added later, such
        as when last online, or an approximate "is_active" field?
    """
    user_list = []
    for user in User.objects.all().prefetch_related("groups"):
        user_list.append(
            {
                "uid": user.id,
                "username": user.username,
                "name": user.first_name,  # Plom uses this as the "name" field
                "groups": user.groups.values_list("name", flat=True),
            }
        )
    return user_list


def get_users_groups_info() -> dict[str, list]:
    """Get a dictionary mapping each user's username to a list of their groups.

    Returns:
        A dict mapping username to a list of the user's groups.
    """
    return {
        user.username: list(user.groups.values_list("name", flat=True))
        for user in User.objects.all()
    }


def get_user_as_dict(username: str) -> dict:
    """Get a User object as a dict."""
    return model_to_dict(User.objects.get_by_natural_key(username))


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
                " they can no longer be deleted."
            )

        deleted_username = user_to_delete.username
        user_to_delete.delete()

    return deleted_username
