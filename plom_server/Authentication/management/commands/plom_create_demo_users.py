# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db import IntegrityError


# -m to get number of scanners and markers
class Command(BaseCommand):
    """Create canned demo users, for demos and testing.

    This is the command for "python manage.py plom_create_demo_users"
    It creates demo users such as 1 manager, 3 scanners and 8 markers.
    Then, add the users to their respective group.
    This command also prints a table with a list of the demo users and
    passwords.
    """

    def handle(self, *args, **options) -> None:
        if not Group.objects.exists():
            raise CommandError(
                "No groups. Please run 'python3 manage.py plom_create_groups' "
                "before running this command"
            )
        number_of_scanners = 3
        number_of_markers = 8
        admin_group = Group.objects.get(name="admin")
        manager_group = Group.objects.get(name="manager")
        marker_group = Group.objects.get(name="marker")
        scanner_group = Group.objects.get(name="scanner")
        demo_group = Group.objects.get(name="demo")
        user_info: dict[str, list[str]] = {"Username": [], "Password": [], "Group": []}

        # Here is to create a single demo admin user
        # is_staff means they can use the django admin tools
        # is_superuser grants all permissions
        username = "demoAdmin"
        password = username
        email = f"{username}@example.com"
        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=True,
            ).groups.add(admin_group, demo_group)
            self.stdout.write(
                f"User {username} created and added to {admin_group} group"
            )
            user_info["Username"].append(username)
            user_info["Password"].append(password)
            user_info["Group"].append(admin_group)
        except IntegrityError as err:
            self.stderr.write(f"{username} already exists!")
            raise CommandError(err)
        except Group.DoesNotExist as err:
            self.stderr.write(f"Admin group {admin_group} does not exist.")
            raise CommandError(err)

        # create managers
        for username, password in (
            ("demoManager1", "demoManager1"),
            ("manager", "1234"),
        ):
            email = f"{username}@example.com"
            try:
                User.objects.create_user(
                    username=username, email=email, password=password
                ).groups.add(manager_group, demo_group)
                self.stdout.write(
                    f"User {username} created and added to {manager_group} group"
                )
                user_info["Username"].append(username)
                user_info["Password"].append(password)
                user_info["Group"].append(manager_group)
            except IntegrityError as err:
                self.stderr.write(f"{username} already exists!")
                raise CommandError(err)

        # create scanners
        for n in range(1, number_of_scanners + 1):
            username = f"demoScanner{n}"
            password = username
            email = f"{username}@example.com"
            if User.objects.filter(username=username).exists():
                self.stderr.write(f'User "{username}" already exists, skipping')
            else:
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                user.groups.add(scanner_group, demo_group)
                user.is_active = True
                user.save()

                self.stdout.write(
                    f"User {username} created and added to {scanner_group} group"
                )
                user_info["Username"].append(username)
                user_info["Password"].append(password)
                user_info["Group"].append(scanner_group)

        # create markers
        for n in range(1, number_of_markers + 1):
            username = f"demoMarker{n}"
            password = username
            email = f"{username}@example.com"
            if User.objects.filter(username=username).exists():
                self.stderr.write(f'User "{username}" already exists, skipping')
            else:
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                user.groups.add(marker_group, demo_group)
                user.is_active = True
                user.save()

                self.stdout.write(
                    f"User {username} created and added to {marker_group} group"
                )
                user_info["Username"].append(username)
                user_info["Password"].append(password)
                user_info["Group"].append(marker_group)

        self.stdout.write("\nDemo usernames and passwords")
        self.stdout.write(
            str(tabulate(user_info, headers="keys", tablefmt="simple_outline"))
        )
