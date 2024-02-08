# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer


from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from tabulate import tabulate


# -m to get number of scanners and markers
class Command(BaseCommand):
    """Create canned demo users, for demos and testing.

    This is the command for "python manage.py plom_create_demo_users"
    It creates demo users such as 1 manager, 3 scanners and 8 markers.
    Then, add the users to their respective group.
    This command also prints a table with a list of the demo users and
    passwords.
    """

    def handle(self, *args, **options):
        if not Group.objects.exists():
            raise CommandError(
                "No groups! Please run 'python3 manage.py plom_create_groups' "
                "before running this command!"
            )
        # TODO: remove later, avoiding a big indent diff with no changes...
        if True:
            number_of_scanners = 3
            number_of_markers = 8
            admin_group = Group.objects.get(name="admin")
            manager_group = Group.objects.get(name="manager")
            marker_group = Group.objects.get(name="marker")
            scanner_group = Group.objects.get(name="scanner")
            demo_group = Group.objects.get(name="demo")
            exist_usernames = [str(username) for username in User.objects.all()]
            admin_info = {"Username": [], "Password": []}
            manager_info = {"Username": [], "Password": []}
            scanner_info = {"Username": [], "Password": []}
            marker_info = {"Username": [], "Password": []}
            email = "@example.com"

            admin = "demoAdmin"
            manager = "demoManager1"
            scanner = "demoScanner"
            marker = "demoMarker"

            # Here is to create a single demo admin user
            try:
                User.objects.create_superuser(
                    username=admin,
                    email=admin + email,
                    password="password",
                    is_staff=True,
                    is_superuser=True,
                ).groups.add(admin_group, demo_group)
                self.stdout.write(f"{admin} created and added to {admin_group} group!")

            except IntegrityError as err:
                self.stderr.write(f"{admin} already exists!")
                raise CommandError(err)
            except Group.DoesNotExist as err:
                self.stderr.write(f"Admin group {admin_group} does not exist.")
                raise CommandError(err)

            admin_info["Username"].append(admin)
            admin_info["Password"].append("password")

            # Here is to create a single demo manager user
            try:
                User.objects.create_user(
                    username=manager, email=manager + email, password=manager
                ).groups.add(manager_group, demo_group)
                self.stdout.write(
                    f"{manager} created and added to {manager_group} group!"
                )
                User.objects.create_user(
                    username="manager", email="manager" + email, password="1234"
                ).groups.add(manager_group, demo_group)
                self.stdout.write(
                    f"{manager} created and added to {manager_group} group!"
                )
            except IntegrityError as err:
                self.stderr.write(f"{manager} already exists!")
                raise CommandError(err)

            manager_info["Username"].append(manager)
            manager_info["Password"].append(manager)
            manager_info["Username"].append("manager")
            manager_info["Password"].append("1234")

            # create scanners
            for n in range(1, number_of_scanners + 1):
                scanner_username = scanner + str(n)
                scanner_password = scanner_username
                scanner_info["Username"].append(scanner_username)
                scanner_info["Password"].append(scanner_password)
                if scanner_username in exist_usernames:
                    self.stderr.write(f"{scanner_username} already exists!")
                else:
                    user = User.objects.create_user(
                        username=scanner_username,
                        email=scanner_username + email,
                        password=scanner_password,
                    )
                    user.groups.add(scanner_group, demo_group)
                    user.is_active = True
                    user.save()

                    self.stdout.write(
                        f"{scanner_username} created and added to {scanner_group} group!"
                    )
            # create markers
            for n in range(1, number_of_markers + 1):
                marker_username = marker + str(n)
                marker_password = marker_username
                marker_info["Username"].append(marker_username)
                marker_info["Password"].append(marker_password)

                if marker_username in exist_usernames:
                    self.stderr.write(f"{marker_username} already exists!")
                else:
                    user = User.objects.create_user(
                        username=marker_username,
                        email=marker_username + email,
                        password=marker_password,
                    )
                    user.groups.add(marker_group, demo_group)
                    user.is_active = True
                    user.save()

                    self.stdout.write(
                        f"{marker_username} created and added to {marker_group} group!"
                    )

            # Here is print the table of demo users
            self.stdout.write("\nAdmin table: demo admin usernames and passwords")
            self.stdout.write(
                str(tabulate(admin_info, headers="keys", tablefmt="fancy_grid"))
            )

            self.stdout.write("\nManager table: demo manager usernames and passwords")
            self.stdout.write(
                str(tabulate(manager_info, headers="keys", tablefmt="fancy_grid"))
            )

            self.stdout.write("\nScanner table: demo scanner usernames and passwords")
            self.stdout.write(
                str(tabulate(scanner_info, headers="keys", tablefmt="fancy_grid"))
            )

            self.stdout.write("\nMarker table: demo marker usernames and passwords")
            self.stdout.write(
                str(tabulate(marker_info, headers="keys", tablefmt="fancy_grid"))
            )
