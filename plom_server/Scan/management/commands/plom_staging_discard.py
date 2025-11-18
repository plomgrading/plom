# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanCastService


class Command(BaseCommand):
    """python3 manage.py plom_staging_discard (username) (bundle name) (bundle_order)."""

    help = "Discard a page from the given bundle at the given order"

    def discard_image_type_from_bundle(
        self, username, bundle_name, order, *, image_type=None
    ):
        scs = ScanCastService()

        if image_type is None:
            self.stdout.write(
                f"Discarding image at position {order} from bundle {bundle_name} as user {username} without type check."
            )
        else:
            image_type = scs.string_to_staging_image_type(image_type)
            self.stdout.write(
                f"Attempting to discardimage of type '{image_type}' at position {order} from bundle {bundle_name} as user {username}"
            )

        # Notice that both user-visible and DB-stored bundle indices are 1-indexed
        # so we **do not** have to add/subtract one when doing these operations.
        try:
            ScanCastService.discard_image_type_from_bundle_cmd(
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
            help="The bundle from which to discard a page",
        )
        parser.add_argument(
            "order",
            type=int,
            help="The order of the page",
        )
        parser.add_argument(
            "--check-type",
            choices=["error", "extra", "known", "unknown"],
            help="When present, the system checks that the page to be discarded is of this type.",
        )

    def handle(self, *args, **options):
        self.discard_image_type_from_bundle(
            options["username"],
            options["bundle"],
            options["order"],
            image_type=options["check_type"],
        )
