# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import ImageRotateService

from plom.plom_exceptions import PlomBundleLockedException


class Command(BaseCommand):
    """python3 manage.py plom_staging_rotate (username) (bundle name) (bundle_order)."""

    help = "Rotate a page of a bundle by 90 degrees counter clockwise."

    def rotate_image_from_bundle(self, username, bundle_name, bundle_order):
        try:
            ImageRotateService().rotate_image_cmd(username, bundle_name, bundle_order)
        except (ValueError, PermissionError, PlomBundleLockedException) as e:
            raise CommandError(e)
        self.stdout.write(
            f"Bundle '{bundle_name}' page {bundle_order} has been rotated."
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="Which user is performing this operation"
        )
        parser.add_argument(
            "bundle",
            type=str,
            help="The bundle from which to rotate a page",
        )
        parser.add_argument(
            "order",
            type=int,
            help="The order of the page",
        )

    def handle(self, *args, **options):
        self.rotate_image_from_bundle(
            options["username"],
            options["bundle"],
            options["order"],
        )
