# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User, Group
from django.db import transaction


@transaction.atomic
def get_users_groups(username: str):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"No such user {username}")
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
def add_user_to_group(username, groupname):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")

    user_obj.groups.add(group_obj)


@transaction.atomic
def remove_user_from_group(username, groupname):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")

    user_obj.groups.remove(group_obj)


@transaction.atomic
def toggle_user_membership_in_group(username, groupname):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")

    if group_obj in user_obj.groups.all():
        user_obj.groups.remove(group_obj)
    else:
        user_obj.groups.add(group_obj)


def is_user_in_group(username, groupname):
    try:
        user_obj = User.objects.get_by_natural_key(username)
    except User.DoesNotExist:
        raise ValueError(f"Cannot find user with name {username}.")
    try:
        group_obj = Group.objects.get_by_natural_key(groupname)
    except Group.DoesNotExist:
        raise ValueError(f"Cannot find group with name {groupname}.")

    return group_obj in user_obj.groups.all()


@transaction.atomic
def toggle_lead_marker_group_membership(username: str):
    if not is_user_in_group(username, "marker"):
        raise ValueError(f"User {username} not a marker.")

    toggle_user_membership_in_group(username, "lead_marker")
