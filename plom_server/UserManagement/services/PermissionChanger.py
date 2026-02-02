# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2025-2026 Colin B. Macdonald

import logging

from django.contrib.auth.models import User, Group
from django.db import transaction

from plom_server.API.services import TokenService
from plom_server.Mark.services import MarkingTaskService
from plom_server.Identify.services import IdentifyTaskService
from plom_server.Authentication.services import AuthService


log = logging.getLogger(__name__)


@transaction.atomic
def get_users_groups(username: str) -> list[str]:
    """Get a list of groups (as strings) from a username."""
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"No such user {username}")
    return _get_users_groups(user_obj)


def _get_users_groups(user_obj: User) -> list[str]:
    return list(user_obj.groups.values_list("name", flat=True))


@transaction.atomic
def toggle_user_active(username: str) -> None:
    """Toggle whether as user is "active", and if now inactive, force logout.

    An inactive user can be thought of as a "soft delete" [1].
    Apparently it "doesn't necessarily control whether or not the user
    can login" [1].

    [1] https://docs.djangoproject.com/en/5.1/ref/contrib/auth/#django.contrib.auth.models.User.is_active
    """
    user = User.objects.get_by_natural_key(username)
    user.is_active = not user.is_active
    user.save()
    # if user is now inactive and a marker then make sure that they are logged
    # out of the API system by removing their API access token.
    if not user.is_active:
        marker_group_obj = Group.objects.get_by_natural_key("marker")
        if marker_group_obj in user.groups.all():
            MarkingTaskService.surrender_all_tasks(user)
            IdentifyTaskService.surrender_all_tasks(user)
            TokenService.drop_api_token(user)


@transaction.atomic
def set_all_users_in_group_active(group_name: str, active: bool):
    """Set the 'is_active' field of all users in the given group to the given boolean."""
    for user in Group.objects.get(name=group_name).user_set.all():
        # explicitly exclude managers here
        if user.groups.filter(name="manager").exists():
            continue
        user.is_active = active
        user.save()


def set_all_scanners_active(active: bool):
    """Set the 'is_active' field of all scanner-users to the given boolean."""
    set_all_users_in_group_active("scanner", active)


def set_all_markers_active(active: bool):
    """Set the 'is_active' field of all marker-users to the given boolean.

    If de-activating markers, then those users also have their
    marker-client access-token revoked (ie client is logged out) and
    any outstanding tasks revoked.
    """
    # if de-activating markers then we also need to surrender tasks and log them out
    # of the API, see Issue #3084.
    set_all_users_in_group_active("marker", active)
    # loop over all (now) deactivated markers, log them out and surrender their tasks
    if not active:
        for user in Group.objects.get(name="marker").user_set.all():
            MarkingTaskService.surrender_all_tasks(user)
            IdentifyTaskService.surrender_all_tasks(user)
            TokenService.drop_api_token(user)


def _add_user_to_group(user_obj: User, groupname: str) -> None:
    """Low-level routine to add user to group, does not enforce dependencies, fewer checks."""
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")
    user_obj.groups.add(group_obj)


def _remove_user_from_group(user_obj: User, groupname: str) -> None:
    """Low-level routine to user from group, with few checks."""
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")
    user_obj.groups.remove(group_obj)


def is_user_in_group(username: str, groupname: str) -> bool:
    """Check if a particular username (a string) is in a groupname (also a string)."""
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")
    return _is_user_in_group(user_obj, groupname)


def _is_user_in_group(user_obj: User, groupname: str) -> bool:
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")
    return group_obj in user_obj.groups.all()


@transaction.atomic
def toggle_lead_marker_group_membership(username: str) -> None:
    """Toggle leader marker status on a marker account.

    For backwards compatibility, promoting a marker to "lead_marker"
    also makes them an "identifier", but not in reverse.

    Raises:
        ValueError: if the user is not a "marker".
    """
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")

    if not _is_user_in_group(user_obj, "marker"):
        raise ValueError(f"User {username} not a marker.")

    if _is_user_in_group(user_obj, "lead_marker"):
        _remove_user_from_group(user_obj, "lead_marker")
    else:
        _add_user_to_group(user_obj, "lead_marker")
        # for backwards compat, we enable identifier (but not in reverse)
        _add_user_to_group(user_obj, "identifier")


def change_user_groups(
    username: str, groups: list[str], *, whoami: str | None = None
) -> list[str]:
    """Change to which groups a user belongs, respecting implications.

    Args:
        username: which user to change.
        groups: which groups we would like them in.

    Keywords Args:
        whoami: optional username string of the calling user.
            If you pass this, we'll prevent managers from
            locking themselves out of the manager group.

    Returns:
        The list of strings of the groupnames that were actually
        set.  Because some groups depend on others, you might get
        a superset of the input.

    There are various restrictions.  For example, you may not remove
    all users from the "manager" group.  You may not change membership
    of the "admin" group.

    Raises:
        RuntimeError: some sort of footgun was prevented, such as you
            may not lock yourself out of your own manager account.
        ValueError: someone tried to do something illegal.
    """
    groups = AuthService.apply_group_name_implications(groups)
    if "admin" in groups:
        raise ValueError('Cannot change membership from the "admin" group')

    with transaction.atomic():
        try:
            # TODO: select for update?  But we never user_obj.save...?
            # TODO: this is something about many-to-many
            user_obj = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            raise ValueError(f"Cannot find user with name {username}.")

        # If removing manager access, ensure there will still *be* managers...
        # we're inside an atomic block to prevent races around this.
        current_groups = _get_users_groups(user_obj)
        if "manager" in current_groups and "manager" not in groups:
            num_managers = User.objects.filter(groups__name="manager").count()
            if num_managers < 2:
                raise RuntimeError(
                    f'Removing manager access from "{username}" would'
                    " leave no manager accounts"
                )

        for g in AuthService.plom_user_groups_list:
            if g == "admin":
                continue
            if g in groups:
                # TODO: some pre-fetching or similar to avoid looking up groups?
                _add_user_to_group(user_obj, g)
            else:
                if whoami is not None:
                    if whoami == username and g == "manager":
                        msg = (
                            f'Cowardly preventing "{username}" from locking'
                            " themselves out of their own manager account"
                        )
                        log.warn(msg)
                        raise RuntimeError(msg)
                _remove_user_from_group(user_obj, g)
    return groups
