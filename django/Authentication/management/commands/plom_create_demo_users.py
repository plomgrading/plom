from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError


class Command(BaseCommand):
    def handle(self, *args, **options):
        range_of_scanners_markers = 5
        manager_group = Group.objects.get(name='manager')
        marker_group = Group.objects.get(name='marker')
        scanner_group = Group.objects.get(name='scanner')
        exist_usernames = [str(username) for username in User.objects.all()]
        email = '@plom.ca'

        # Here is to create a single manager user
        manager = 'manager1'
        scanner = 'scanner'
        scanner_username = ''
        marker_username = ''
        marker = 'marker'
        try:
            User.objects.create_user(username=manager,
                                     email=manager + email,
                                     password=manager).groups.add(manager_group)
            print(f'{manager} created and added to {manager_group} group!')

        except IntegrityError:
            print(f'{manager} already exists!')

        try:
            for number_of_scanner_marker in range(1, range_of_scanners_markers + 1):
                scanner_username = scanner + str(number_of_scanner_marker)
                marker_username = marker + str(number_of_scanner_marker)
                User.objects.create_user(username=scanner_username,
                                         email=scanner_username + email,
                                         password=scanner_username).groups.add(scanner_group)
                print(f'{scanner_username} created and added to {scanner_group} group!')
                User.objects.create_user(username=marker_username,
                                         email=marker_username + email,
                                         password=marker_username).groups.add(marker_group)
                print(f'{marker_username} created and added to {marker_group} group!')
        except IntegrityError:
            print(f'{scanner_username} already exists!')
            print(f'{marker_username} already exists!')
        # demon_users.append(manager)
        # # Here is to create a list of demo scanner and marker users
        # scanner = 'scanner'
        # marker = 'marker'
        # for index in range(1, number_of_users + 1):
        #     demon_users.append(scanner + str(index))
        #     demon_users.append(marker + str(index))
        #
        # print(demon_users)
        #
        # test = 'manager'
        # if test in str(User.objects.all().get(username=test)):
        #     print("Yes")
        # else:
        #     print("No")
