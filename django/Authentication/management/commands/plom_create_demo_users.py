# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from tabulate import tabulate

from Connect.services import CoreUsersService


# -m to get number of scanners and markers
class Command(BaseCommand):
    """
    This is the command for "python manage.py plom_create_demo_users"
    It creates demo users such as 1 manager, 5 scanners and 5 markers.
    Then, add the users to their respective group.
    This command also prints a table with a list of the demo users and
    passwords.
    """

    def handle(self, *args, **options):

        # Check to see if there are any groups created
        exist_groups = [str(group) for group in Group.objects.all()]
        if not exist_groups:
            print(
                "\nNo groups created! Please run python manage.py plom_create_groups "
                "to create groups first before running this command!\n"
            )
        else:
            range_of_scanners_markers = 5
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
            email = "@plom.ca"

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
                print(f"{admin} created and added to {admin_group} group!")

            except (IntegrityError, Group.DoesNotExist):
                print(f"{admin} already exists!")
            admin_info["Username"].append(admin)
            admin_info["Password"].append("password")

            # Here is to create a single demo manager user
            try:
                User.objects.create_user(
                    username=manager, email=manager + email, password=manager
                ).groups.add(manager_group, demo_group)
                print(f"{manager} created and added to {manager_group} group!")

            except IntegrityError:
                print(f"{manager} already exists!")
            manager_info["Username"].append(manager)
            manager_info["Password"].append(manager)

            # for updating a connected core server
            core = CoreUsersService()

            # Here is to create 5 scanners and markers
            for number_of_scanner_marker in range(1, range_of_scanners_markers + 1):
                scanner_username = scanner + str(number_of_scanner_marker)
                scanner_password = scanner_username + "_"
                scanner_info["Username"].append(scanner_username)
                scanner_info["Password"].append(scanner_password)

                marker_username = marker + str(number_of_scanner_marker)
                marker_password = marker_username + "_"
                marker_info["Username"].append(marker_username)
                marker_info["Password"].append(marker_password)

                if scanner_username in exist_usernames:
                    print(f"{scanner_username} already exists!")
                else:
                    User.objects.create_user(
                        username=scanner_username,
                        email=scanner_username + email,
                        password=scanner_password,
                    ).groups.add(scanner_group, demo_group)
                    user = User.objects.get(username=scanner_username)
                    user.is_active = True
                    user.save()

                    print(
                        f"{scanner_username} created and added to {scanner_group} group!"
                    )

                    # add to core server (if a valid connection exists)
                    core.create_core_user(scanner_username, scanner_password)

                if marker_username in exist_usernames:
                    print(f"{marker_username} already exists!")
                else:
                    User.objects.create_user(
                        username=marker_username,
                        email=marker_username + email,
                        password=marker_password,
                    ).groups.add(marker_group, demo_group)
                    user = User.objects.get(username=marker_username)
                    user.is_active = True
                    user.save()

                    print(
                        f"{marker_username} created and added to {marker_group} group!"
                    )

                    # add to core server (if there is a valid connection)
                    core.create_core_user(marker_username, marker_password)

            # Here is print the table of demo users
            print("")
            print("Admin")
            print("Table: List of demo admin username and password")
            print(tabulate(admin_info, headers="keys", tablefmt="fancy_grid"))

            print("")
            print("Manager")
            print("Table: List of demo manager usernames and passwords")
            print(tabulate(manager_info, headers="keys", tablefmt="fancy_grid"))

            print("")
            print("Scanners")
            print("Table: List of demo scanner usernames and passwords")
            print(tabulate(scanner_info, headers="keys", tablefmt="fancy_grid"))

            print("")
            print("Markers")
            print("Table: List of demo scanner usernames and passwords")
            print(tabulate(marker_info, headers="keys", tablefmt="fancy_grid"))

            print("Note: If you change the demo user password, please remember it.")
