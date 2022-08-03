from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    def handle(self, *args, **options):
        group_list = ['admin', 'manager', 'marker', 'scanner']
        exist_groups = [str(group) for group in Group.objects.all()]

        for group in group_list:
            if group not in exist_groups:
                Group(name=group).save()
                print(f'{group} has been added!')
            else:
                print(f'{group} exist already!')



