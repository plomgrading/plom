# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, User

from UserManagement.services import PermissionChanger


class Command(BaseCommand):
    """Show users membership of the marker and lead markers groups.

    Allow toggling of membership of the lead-marker group.
    """
    def show_group_membership(self, username):
        user_in_groups = PermissionChanger.get_users_groups(username)
        self.stdout.write(f"User {username} is in groups {user_in_groups}")

    def toggle_membership_of_leadmarker_group(self, username):
        try:
            user_obj = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            raise CommandError("No such user")
        user_in_groups = user_obj.groups.values_list("name", flat=True)
        if "marker" not in user_in_groups:
            self.stdout.write(
                f"User {username} is not in the marker group, cannot change lead-marker group membership."
            )
            return

        lead_marker_group = Group.objects.get(name="lead_marker")
        if "lead_marker" in user_in_groups:
            self.stdout.write(
                f"User {username} is in the lead-marker group - removing them."
            )
            user_obj.groups.remove(lead_marker_group)
        else:
            self.stdout.write(
                f"User {username} is not in the lead-marker group - adding them."
            )
            user_obj.groups.add(lead_marker_group)
        user_obj.save()

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Which user to operator on",
        )
        parser.add_argument(
            "--toggle",
            action="store_true",
            help="Toggle the given user in and out of the lead-marker group.",
        )

    def handle(self, *args, **options):
        if options["toggle"]:
            self.toggle_membership_of_leadmarker_group(options["username"])
        else:
            self.show_group_membership(options["username"])
