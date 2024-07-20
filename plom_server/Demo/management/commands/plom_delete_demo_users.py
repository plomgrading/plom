# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    """Remove the canned demo users.

    This is the command for "python manage.py plom_delete_demo_users.py
    It deletes all the users within demo group.
    """

    def handle(self, *args, **options):
        for demo_user in User.objects.filter(groups__name="demo"):
            demo_user.delete()

        self.stdout.write("All demo users have been deleted!")
