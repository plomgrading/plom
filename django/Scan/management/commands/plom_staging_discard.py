# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand

from Scan.services import ScanCastService


def discard_image_type_from_bundle(username, bundle_name, order, image_type):
    # TODO - put in an "Are you sure" here for error pages?

    print(
        f"Attempting to discardimage of type '{image_type}' at position {order} from bundle {bundle_name} as user {username}"
    )
    # Notice that user-visible orders start from 1 (like page numbers)
    # while in the db they start from zero, so we must deduct 1 when
    # we pass it to the scan-cast-service
    ScanCastService().discard_image_type_from_bundle_cmd(
        username, bundle_name, order - 1, image_type
    )


class Command(BaseCommand):
    """
    commands:
        python3 manage.py plom_staging_discard unknown (bundle name) (bundle_order)
    """

    help = "Discard a page from the given bundle at the given order"

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="Discard page from given bundle.",
        )

        sp.add_parser("unknown", help="Discard an unknown page.")
        sp.add_parser("known", help="Discard a known page.")
        sp.add_parser("extra", help="Discard an extra page.")
        sp.add_parser("error", help="Discard an error page (discouraged).")
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

    def handle(self, *args, **options):
        if options["command"] in ["unknown", "known", "extra", "error"]:
            discard_image_type_from_bundle(
                options["username"],
                options["bundle"],
                options["order"],
                options["command"],
            )
        else:
            self.print_help("manage.py", "plom_staging_discard")
