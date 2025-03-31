# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanCastService


class Command(BaseCommand):
    """python3 manage.py plom_staging_extralise (username) (bundle name) (bundle_order)."""

    help = "Cast to extra a page from the given bundle at the given order"

    def extralise_image_from_bundle(
        self, username, bundle_name, order, *, image_type=None
    ):
        scs = ScanCastService()

        if image_type is None:
            self.stdout.write(
                f"Extralise image at position {order} from bundle {bundle_name} as user {username} without type check."
            )
        else:
            image_type = scs.string_to_staging_image_type(image_type)
            self.stdout.write(
                f"Attempting to extralise image of type '{image_type}' at position {order} from bundle {bundle_name} as user {username}"
            )
        try:
            ScanCastService().extralise_image_from_bundle_cmd(
                username, bundle_name, order, image_type=image_type
            )
        except ValueError as err:
            raise CommandError(err)
        self.stdout.write("Action completed")

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="Which user is performing this operation"
        )
        parser.add_argument(
            "bundle",
            type=str,
            help="The bundle from which to extralise a page",
        )
        parser.add_argument(
            "order",
            type=int,
            help="The order of the page",
        )
        parser.add_argument(
            "--check-type",
            choices=["discard", "error", "known", "unknown"],
            help="When present, the system checks that the page to be extralised is of this type.",
        )

    def handle(self, *args, **options):
        self.extralise_image_from_bundle(
            options["username"],
            options["bundle"],
            options["order"],
            image_type=options["check_type"],
        )
