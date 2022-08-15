from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    def handle(self, *args, **options):
        for demo_user in User.objects.filter(groups__name='demo'):
            demo_user.delete()

        print('All demo users have been deleted!')

