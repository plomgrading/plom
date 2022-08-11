from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
# pip install tabulate
from tabulate import tabulate


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
        marker = 'marker'
        try:
            User.objects.create_user(username=manager,
                                     email=manager + email,
                                     password=manager).groups.add(manager_group)
            print(f'{manager} created and added to {manager_group} group!')

        except IntegrityError:
            print(f'{manager} already exists!')

        for number_of_scanner_marker in range(1, range_of_scanners_markers + 1):
            scanner_username = scanner + str(number_of_scanner_marker)
            marker_username = marker + str(number_of_scanner_marker)

            if scanner_username in exist_usernames:
                print(f'{scanner_username} already exists!')
            else:
                User.objects.create_user(username=scanner_username,
                                         email=scanner_username + email,
                                         password=scanner_username).groups.add(scanner_group)
                print(f'{scanner_username} created and added to {scanner_group} group!')

            if marker_username in exist_usernames:
                print(f'{marker_username} already exists!')
            else:
                User.objects.create_user(username=marker_username,
                                         email=marker_username + email,
                                         password=marker_username).groups.add(marker_group)
                print(f'{marker_username} created and added to {marker_group} group!')


