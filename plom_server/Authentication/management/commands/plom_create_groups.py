# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.core.management.base import BaseCommand

from plom_server.Authentication.services import AuthenticationServices


class Command(BaseCommand):
    """Create the user groups.

    This is the command for "python manage.py plom_create_groups".
    It creates the groups needed for Plom to work.

    Any existing superusers will be automatically added to the admin
    group (but you can add others later).
    """

    def handle(self, *args, **options):
        [added, already] = AuthenticationServices.create_groups()
        for group in already:
            self.stderr.write(f'Group "{group}" already exists')
        for group in added:
            self.stdout.write(f'Group "{group}" has been added')
        [added, already] = AuthenticationServices.ensure_superusers_in_admin_group()
        admin = "admin"
        for u in already:
            self.stderr.write(f'Superuser "{u}" is already in the "{admin}" group')
        for u in added:
            self.stdout.write(f'Added superuser "{u}" to the "{admin}" group')
