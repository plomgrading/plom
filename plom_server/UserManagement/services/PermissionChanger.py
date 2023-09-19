# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User, Group
from django.db import transaction


@transaction.atomic
def get_users_groups(username: str):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError("No such user")
    return list(user_obj.groups.values_list("name", flat=True))


@transaction.atomic
def toggle_user_active(username: str):
    user_to_change = User.objects.get_by_natural_key(username)
    user_to_change.is_active = not user_to_change.is_active
    user_to_change.save()


@transaction.atomic
def set_all_users_in_group_active(group_name: str, active: bool):
    for user in Group.objects.get(name=group_name).user_set.all():
        user.is_active = active
        user.save()


def set_all_scanners_active(active: bool):
    set_all_users_in_group_active("scanner", active)


def set_all_markers_active(active: bool):
    set_all_users_in_group_active("marker", active)


@transaction.atomic
def toggle_lead_marker_group_membership(username: str):
    user_obj = User.objects.get_by_natural_key(username)
    marker_group = Group.objects.get(name="marker")
    # user must be in the marker group
    if marker_group not in user_obj.groups.all():
        raise ValueError(f"User {username} not a marker.")

    lead_marker_group = Group.objects.get(name="lead_marker")
    if lead_marker_group in user_obj.groups.all():
        user_obj.groups.remove(lead_marker_group)
    else:
        user_obj.groups.add(lead_marker_group)
    user_obj.save()
