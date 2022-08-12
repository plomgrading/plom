from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
# pip install tabulate
from tabulate import tabulate


class Command(BaseCommand):
    """
    This is the command for "python manage.py plom_create_demo_users"
    It creates demo users such as 1 manager, 5 scanners and 5 markers.
    Then, add the users to their respective group.
    This command also prints a table with a list of the demo users and
    passwords.
    """
    def handle(self, *args, **options):
        range_of_scanners_markers = 5
        manager_group = Group.objects.get(name='manager')
        marker_group = Group.objects.get(name='marker')
        scanner_group = Group.objects.get(name='scanner')
        demo_group = Group.objects.get(name='demo')
        exist_usernames = [str(username) for username in User.objects.all()]
        demo_usernames = []
        demo_user_password = []
        manager_info = {
            'Username': None,
            'Password': None
        }
        scanner_info = {
            'Username': None,
            'Password': None
        }
        marker_info = {
            'Username': None,
            'Password': None
        }
        email = '@plom.ca'

        manager = 'manager1'
        scanner = 'scanner'
        marker = 'marker'

        print(User.objects.all().filter(groups__name='demo'))

        # Here is to create a single manager user
        try:
            User.objects.create_user(username=manager,
                                     email=manager + email,
                                     password=manager).groups.add(manager_group, demo_group)
            print(f'{manager} created and added to {manager_group} group!')

        except IntegrityError:
            print(f'{manager} already exists!')
        manager_info['Username'], manager_info['Password'] = manager

        # Here is to create 5 scanners and markers
        for number_of_scanner_marker in range(1, range_of_scanners_markers + 1):
            scanner_username = scanner + str(number_of_scanner_marker)
            demo_usernames.append(scanner_username)
            demo_user_password.append(scanner_username)

            marker_username = marker + str(number_of_scanner_marker)
            demo_usernames.append(marker_username)
            demo_user_password.append(marker_username)

            if scanner_username in exist_usernames:
                print(f'{scanner_username} already exists!')
            else:
                User.objects.create_user(username=scanner_username,
                                         email=scanner_username + email,
                                         password=scanner_username).groups.add(scanner_group, demo_group)
                print(f'{scanner_username} created and added to {scanner_group} group!')

            if marker_username in exist_usernames:
                print(f'{marker_username} already exists!')
            else:
                User.objects.create_user(username=marker_username,
                                         email=marker_username + email,
                                         password=marker_username).groups.add(marker_group, demo_group)
                print(f'{marker_username} created and added to {marker_group} group!')

        print('')
        print('Manger')
        print('Table: List of demo manager usernames and passwords')
        # here will display Manager

        print('')
        print('Manger')
        print('Table: List of demo manager usernames and passwords')

        # print(tabulate(info, headers='keys', tablefmt='fancy_grid'))
# TODO: report user in better order
