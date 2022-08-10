from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    def handle(self, *args, **options):
        email = '@plom.ca'
        manager_group = Group.objects.get(name='manager')
        marker_group = Group.objects.get(name='marker')
        scanner_group = Group.objects.get(name='scanner')

        # Here is to create a single manager user
        manager = 'manager1'
        User.objects.create_user(username=manager,
                                 email=manager+email,
                                 password=manager).groups.add(manager_group)

