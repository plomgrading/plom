from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    def handle(self, *args, **options):
        number_of_users = 5
        demon_users = []
        email = '@plom.ca'
        manager_group = Group.objects.get(name='manager')
        marker_group = Group.objects.get(name='marker')
        scanner_group = Group.objects.get(name='scanner')

        # Here is to create a single manager user
        manager = 'manager1'
        User.objects.create_user(username=manager,
                                 email=manager + email,
                                 password=manager).groups.add(manager_group)
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
