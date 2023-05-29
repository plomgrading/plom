# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.core.management.base import BaseCommand, CommandError

from Scan.services import ImageRotateService


class Command(BaseCommand):
    """
    python3 manage.py plom_staging_rotate (username) (bundle name) (bundle_order)
    """

    help = "Rotate a page from the given bundle name and bundle order"

    def rotate_image_from_bundle(self, username, bundle_name, bundle_order):
        scanner = ImageRotateService()
        img_layout = scanner.rotate_image_cmd(username, bundle_name, bundle_order)
        self.stdout.write(f"Bundle '{bundle_name}' page {bundle_order} has been rotated.")
        self.stdout.write(f"Image orientation: {img_layout}")

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