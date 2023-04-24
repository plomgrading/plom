# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand

from Scan.services import ScanCastService


def unknowify_image_type_from_bundle(username, bundle_name, order, image_type):
    # TODO - put in an "Are you sure" here for error pages?

    print(
        f"Attempting to cast to unknown image of type '{image_type}' at position {order} from bundle {bundle_name} as user {username}"
    )
    # Notice that user-visible orders start from 1 (like page numbers)
    # while in the db they start from zero, so we must deduct 1 when
    # we pass it to the scan-cast-service
    ScanCastService().unknowify_image_type_from_bundle_cmd(
        username, bundle_name, order - 1, image_type
    )


class Command(BaseCommand):
    """
    commands:
        python3 manage.py plom_staging_unknowify_page discard (bundle name) (bundle_order)
    """

    help = "Cast to unknown a page from the given bundle at the given order"

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="Unknowify page from given bundle.",
        )

        sp.add_parser("discard", help="Unknowify a discard page.")
        sp.add_parser("known", help="Unknowify an known page.")
        sp.add_parser("extra", help="Unknowify an extra page.")
        sp.add_parser("error", help="Unknowify an error page (discouraged).")
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

    def handle(self, *args, **options):
        if options["command"] in ["discard", "known", "extra", "error"]:
            unknowify_image_type_from_bundle(
                options["username"],
                options["bundle"],
                options["order"],
                options["command"],
            )
        else:
            self.print_help("manage.py", "plom_staging_discard")
