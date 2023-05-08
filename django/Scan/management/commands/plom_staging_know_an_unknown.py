# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from tabulate import tabulate

from django.core.management.base import BaseCommand
from Scan.services import ScanCastService, ScanService
from Papers.services.validated_spec_service import SpecificationService
from plom.scan.question_list_utils import check_question_list


class Command(BaseCommand):
    """
    commands:
        python3 manage.py plom_staging_know_an_unknown (bundle name) (bundle_order) (paper_number) (page_number)
    """

    help = """Fix an unknown page as being a known page of the given paper, page."""

    def list_missing_paper_page_numbers(self, bundle_name):
        scanner = ScanService()
        missing_papers_pages = scanner.get_bundle_missing_paper_page_numbers_cmd(
            bundle_name
        )
        if len(missing_papers_pages) == 0:
            self.stdout.write(
                "No papers with missing known-pages (papers have zero or all their known pages)"
            )
            return

        self.stdout.write(f"Papers with missing pages in bundle {bundle_name}:")
        for (pn, pg_list) in missing_papers_pages:
            self.stdout.write(f"\t{pn}: {pg_list}")

    def list_unknown_pages(self, bundle_name):
        scanner = ScanService()
        bundle_page_list = scanner.get_bundle_unknown_pages_info_cmd(bundle_name)

        self.stdout.write(
            tabulate(bundle_page_list, headers="keys", tablefmt="simple_outline")
        )

    # def assign_extra_page(
    #     self, username, bundle_name, index, paper_number, question_list
    # ):
    #     scs = ScanCastService()
    #     scs.assign_extra_page_cmd(
    #         username, bundle_name, index, paper_number, question_list
    #     )

    def add_arguments(self, parser):
        parser.add_argument(
            "bundle",
            type=str,
            help="The bundle on which to operate",
        )
        sp = parser.add_subparsers(
            dest="command",
            description="Assign an extra page to a paper and questions.",
        )
        sp.add_parser("unknowns", help="List the unknown pages in the bundle.")
        sp.add_parser(
            "missing", help="List the missing known paper-numbers in the bundle."
        )
        spa = sp.add_parser(
            "assign", help="Assign the known page a paper-number and page-number."
        )
        spa.add_argument("username", type=str, help="username doing the assigning.")
        spa.add_argument(
            "-i" "--index", type=int, help="index of page within the bundle (from one)"
        )
        spa.add_argument(
            "-p", "--paper", type=int, help="the paper-number of the known-page"
        )
        spa.add_argument(
            "-g", "--page", type=int, help="the page-number of the known-page"
        )

    def handle(self, *args, **options):
        if options["command"] == "unknowns":
            self.list_unknown_pages(options["bundle"])
        elif options["command"] == "missing":
            self.list_missing_paper_page_numbers(options["bundle"])
        # elif options["command"] == "assign":
        #     n_questions = SpecificationService().get_n_questions()
        #     question_list = check_question_list(options["question"][0], n_questions)
        #     self.assign_extra_page(
        #         options["username"],
        #         options["bundle"],
        #         options["index"],
        #         options["paper"],
        #         question_list,
        #     )
        else:
            self.print_help("manage.py", "plom_know_an_unknown")
