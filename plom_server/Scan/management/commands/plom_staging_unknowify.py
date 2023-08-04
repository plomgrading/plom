# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanCastService


class Command(BaseCommand):
    """python3 manage.py plom_staging_unknowify (username) (bundle name) (bundle_order)."""

    help = "Cast to unknown a page from the given bundle at the given order"

    def unknowify_image_type_from_bundle(
        self, username, bundle_name, order, *, image_type=None
    ):
        scs = ScanCastService()

        if image_type is None:
            self.stdout.write(
                f"Unknowify image at position {order} from bundle {bundle_name} as user {username} without type check."
            )
        else:
            image_type = scs.string_to_staging_image_type(image_type)
            self.stdout.write(
                f"Attempting to unknowify image of type '{image_type}' at position {order} from bundle {bundle_name} as user {username}"
            )
        try:
            ScanCastService().unknowify_image_type_from_bundle_cmd(
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
            help="The bundle from which to unknowify a page",
        )
        parser.add_argument(
            "order",
            type=int,
            help="The order of the page",
        )
        parser.add_argument(
            "--check-type",
            choices=["discard", "error", "extra", "known"],
            help="When present, the system checks that the page to be unknowified is of this type.",
        )

    def handle(self, *args, **options):
        self.unknowify_image_type_from_bundle(
            options["username"],
            options["bundle"],
            options["order"],
            image_type=options["check_type"],
        )
