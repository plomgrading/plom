# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import ScanCastService


class Command(BaseCommand):
    """python3 manage.py plom_staging_unknowify (username) (bundle name) (bundle_order)."""

    help = "Cast to unknown a page from the given bundle at the given order"

    def unknowify_image_type_from_bundle(
        self,
        username: str,
        bundle_name: str,
        order: int,
        *,
        image_type_str: str | None = None,
    ) -> None:
        if image_type_str is None:
            self.stdout.write(
                f"Unknowify image at position {order} from bundle {bundle_name} "
                f"as user {username} without type check."
            )
        else:
            image_type = ScanCastService().string_to_staging_image_type(image_type_str)
            self.stdout.write(
                f"Attempting to unknowify image of type '{image_type}' "
                f"at position {order} from bundle {bundle_name} as user {username}"
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
            help="""
                When present, the system checks that the page to be
                unknowified is of this type.
            """,
        )

    def handle(self, *args, **options):
        self.unknowify_image_type_from_bundle(
            options["username"],
            options["bundle"],
            options["order"],
            image_type_str=options["check_type"],
        )
