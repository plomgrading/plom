# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User


class Command(BaseCommand):
    """Create the user groups.

    This is the command for "python manage.py plom_create_groups"
    It creates admin, manager, marker, and scanner groups. Then,
    any superusers will be added to the admin group.
    """

    def handle(self, *args, **options):
        group_list = ["admin", "manager", "marker", "scanner", "demo", "lead_marker"]
        # get all the existing groups in a list
        exist_groups = [str(group) for group in Group.objects.all()]

        # get all the groups
        for group in group_list:
            if group not in exist_groups:
                Group(name=group).save()
                self.stdout.write(f"{group} has been added!")
            else:
                self.stderr.write(f"{group} exist already!")

        # now get the admin group
        admin_group = Group.objects.get(name="admin")
        # get all superusers
        for user in User.objects.filter(is_superuser=True):
            if user.groups.filter(name="admin").exists():
                self.stderr.write(
                    f"Superuser {user.username} is already in the 'admin' group."
                )
            else:
                user.groups.add(admin_group)
                user.save()
                self.stdout.write(
                    f"Added superuser {user.username} to the 'admin' group"
                )
