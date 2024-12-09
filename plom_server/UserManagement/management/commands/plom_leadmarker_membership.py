# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import PermissionChanger


class Command(BaseCommand):
    """Show users membership of the marker and lead markers groups.

    Also allow toggling of membership of the lead-marker group.
    """

    def show_group_membership(self, username):
        try:
            user_in_groups = PermissionChanger.get_users_groups(username)
            self.stdout.write(f"User {username} is in groups {user_in_groups}")
        except ValueError as e:
            raise CommandError(e)

    def toggle_membership_of_leadmarker_group(self, username):
        try:
            PermissionChanger.toggle_lead_marker_group_membership(username)
        except ValueError as e:
            raise CommandError(e)
        self.show_group_membership(username)

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Which user to query or set.",
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
