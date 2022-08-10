from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User


class Command(BaseCommand):
    """
    This is the command for "python manage.py plom_create_groups"
    It creates admin, manager, marker, and scanner groups. Then,
    any superusers will be added to the admin group.
    """
    def handle(self, *args, **options):
        group_list = ['admin', 'manager', 'marker', 'scanner']
        # get all the existing groups in a list
        exist_groups = [str(group) for group in Group.objects.all()]

        # get all the groups
        for group in group_list:
            if group not in exist_groups:
                Group(name=group).save()
                print(f'{group} has been added!')
            else:
                print(f'{group} exist already!')

        # now get the admin group
        admin_group = Group.objects.get(name="admin")
        # get all superusers
        for user in User.objects.filter(is_superuser=True):
            if user.groups.filter(name="admin").exists():
                print(f"Superuser {user.username} is already in the 'admin' group.")
            else:
                user.groups.add(admin_group)
                user.save()
                print(f"Added superuser {user.username} to the 'admin' group")

