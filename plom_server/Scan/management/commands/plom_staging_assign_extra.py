# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError

from plom.scan.question_list_utils import check_question_list
from Papers.services import SpecificationService
from ...services import ScanCastService, ScanService


class Command(BaseCommand):
    """python3 manage.py plom_staging_unknowify_page discard (bundle name) (bundle_order)."""

    help = """Assign an extra page to a paper and question(s). Note that
    this command cannot cast a page to the 'extra'-type, instead one
    should use the plom_staging_extralise command."""

    def list_paper_numbers(self, bundle_name):
        scanner = ScanService()
        paper_numbers = scanner.get_bundle_paper_numbers_cmd(bundle_name)
        self.stdout.write(f"Papers in bundle {bundle_name}: {paper_numbers}")

    def list_extra_pages(self, bundle_name):
        scanner = ScanService()
        bundle_page_dict = scanner.get_bundle_extra_pages_info_cmd(bundle_name)
        bundle_page_list = [["order", "status", "info", "rotation"]]
        for ord in sorted(bundle_page_dict.keys()):
            page = bundle_page_dict[ord]
            if page["info"]["paper_number"] and page["info"]["question_list"]:
                bundle_page_list.append(
                    [
                        page["order"],
                        page["status"],
                        f"paper {page['info']['paper_number']}: q{page['info']['question_list']}",
                        page["rotation"],
                    ]
                )
            else:
                bundle_page_list.append(
                    [
                        page["order"],
                        page["status"],
                        "extra page without data",
                        page["rotation"],
                    ]
                )

        self.stdout.write(
            tabulate(bundle_page_list, headers="firstrow", tablefmt="simple_outline")
        )

    def assign_extra_page(
        self, username, bundle_name, index, paper_number, question_list
    ):
        scs = ScanCastService()
        try:
            scs.assign_extra_page_cmd(
                username, bundle_name, index, paper_number, question_list
            )
        except ValueError as e:
            raise CommandError(e)

    def clear_extra_page_data(self, username, bundle_name, index):
        scs = ScanCastService()
        scs.clear_extra_page_cmd(username, bundle_name, index)

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="Assign an extra page to a paper and questions.",
        )
        spl = sp.add_parser("list", help="List the extra pages in the bundle.")
        spl.add_argument(
            "bundle",
            type=str,
            help="The bundle on which to operate",
        )

        spp = sp.add_parser(
            "papers", help="List the known paper-numbers in the bundle."
        )
        spp.add_argument(
            "bundle",
            type=str,
            help="The bundle on which to operate",
        )

        spa = sp.add_parser(
            "assign", help="Assign the extra page a paper-number and question-list."
        )
        spa.add_argument("username", type=str, help="username doing the assigning.")
        spa.add_argument(
            "bundle",
            type=str,
            help="The bundle on which to operate",
        )
        spa.add_argument(
            "-i", "--index", type=int, help="index of page within the bundle (from one)"
        )
        spa.add_argument(
            "-t", "--paper", type=int, help="the paper-number of the extra-page"
        )
        spa.add_argument(
            "-q",
            "--question",
            nargs="?",
            metavar="N",
            help="""
                Which question(s) are answered on this page?
                You can pass a single integer, or a list like `[1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `all` which uploads
                the page to all questions (this is also the default).

                If you pass `dnm` it will be attached to the "do not mark"
                group, making it available to this paper but not generally marked.
            """,
        )
        spc = sp.add_parser(
            "clear",
            help="Clear the extra-page data from the given extra-page in the bundle",
        )
        spc.add_argument("username", type=str, help="username doing the clearing.")
        spc.add_argument(
            "-i", "--index", type=int, help="index of page within the bundle (from one)"
        )

    def handle(self, *args, **options):
        if options["command"] == "list":
            self.list_extra_pages(options["bundle"])
        elif options["command"] == "papers":
            self.list_paper_numbers(options["bundle"])
        elif options["command"] == "assign":
            if options["question"] is None:
                options["question"] = "all"
            n_questions = SpecificationService.get_n_questions()
            question_list = check_question_list(options["question"], n_questions)
            self.assign_extra_page(
                options["username"],
                options["bundle"],
                options["index"],
                options["paper"],
                question_list,
            )
        elif options["command"] == "clear":
            self.clear_extra_page_data(
                options["username"],
                options["bundle"],
                options["index"],
            )
        else:
            self.print_help("manage.py", "plom_staging_assign_extra")
