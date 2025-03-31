# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import PermissionDenied

from ...services import ScanCastService, ScanService


class Command(BaseCommand):
    """Map an unknown or discarded page to a "known" page of a given paper."""

    help = """Fix an unknown or discarded page as being a known page of the given paper, page."""

    def list_missing_paper_page_numbers(self, bundle_name):
        scanner = ScanService()
        try:
            missing_papers_pages = scanner.get_bundle_missing_paper_page_numbers_cmd(
                bundle_name
            )
        except ValueError as err:
            raise CommandError(err) from err

        if len(missing_papers_pages) == 0:
            self.stdout.write(
                "No papers in this bundle with missing known-pages (papers have zero or all their known pages)"
            )
            return

        self.stdout.write(f"Papers with missing pages in bundle {bundle_name}:")
        for pn, pg_list in missing_papers_pages:
            self.stdout.write(f"\t{pn}: {pg_list}")

    def list_unknown_and_discarded_pages(self, bundle_name):
        scanner = ScanService()
        try:
            bundle_unknowns_list = scanner.get_bundle_unknown_pages_info_cmd(
                bundle_name
            )
            bundle_discards_list = scanner.get_bundle_discard_pages_info_cmd(
                bundle_name
            )
        except ValueError as err:
            raise CommandError(err) from err

        self.stdout.write("Unknown pages:")
        self.stdout.write(
            tabulate(bundle_unknowns_list, headers="keys", tablefmt="simple_outline")
        )

        self.stdout.write("Discarded pages:")
        self.stdout.write(
            tabulate(bundle_discards_list, headers="keys", tablefmt="simple_outline")
        )

    def knowify_given_page(
        self, username, bundle_name, bundle_order, paper_number, page_number
    ):
        scs = ScanCastService()
        try:
            scs.knowify_image_from_bundle_name(
                username, bundle_name, bundle_order, paper_number, page_number
            )
            self.stdout.write("Image assigned")
        except (PermissionDenied, ValueError) as err:
            raise CommandError(err) from err

    def add_arguments(self, parser):
        parser.add_argument(
            "bundle",
            type=str,
            help="The bundle on which to operate",
        )
        sp = parser.add_subparsers(
            dest="command",
            description="Set an unknown or discarded page as a given known page of a given paper.",
        )
        sp.add_parser(
            "list", help="List the unknown and discarded pages in the bundle."
        )
        sp.add_parser(
            "missing", help="List the missing known paper-numbers in the bundle."
        )
        spa = sp.add_parser(
            "assign", help="Assign the known page a paper-number and page-number."
        )
        spa.add_argument(
            "-u",
            "--username",
            type=str,
            help="the user performing the assignment (must be in the scanner or manager groups)",
        )
        spa.add_argument(
            "-i", "--index", type=int, help="index of page within the bundle (from one)"
        )
        spa.add_argument(
            "-p", "--paper", type=int, help="the paper-number of the known-page"
        )
        spa.add_argument(
            "-g", "--page", type=int, help="the page-number of the known-page"
        )

    def handle(self, *args, **options):
        if options["command"] == "list":
            self.list_unknown_and_discarded_pages(options["bundle"])
        elif options["command"] == "missing":
            self.list_missing_paper_page_numbers(options["bundle"])
        elif options["command"] == "assign":
            self.knowify_given_page(
                options["username"],
                options["bundle"],
                options["index"],
                options["paper"],
                options["page"],
            )
        else:
            self.print_help("manage.py", "plom_know_an_unknown")
