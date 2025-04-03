# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from plom.scan.question_list_utils import check_question_list
from plom_server.Papers.services import SpecificationService
from ...services import ManageDiscardService


class Command(BaseCommand):
    """Reassign discarded pages.

    Examples:
        python3 manage.py plom_reassign_discard (username) (discardpage pk) -n paper_number -p page_number.
        python3 manage.py plom_reassign_discard (username) (discardpage pk) -n paper_number -q question_index.
    """

    help = "Reassign a (pushed) discarded page as a given fixed or mobile page."

    def reassign_discard_page_to_fixed_page(
        self,
        username: str,
        discard_pk: int,
        paper_number: int,
        *,
        page_number: int,
    ):
        try:
            ManageDiscardService().reassign_discard_page_to_fixed_page_cmd(
                username, discard_pk, paper_number, page_number
            )
        except ValueError as e:
            raise CommandError(e)

    def reassign_discard_page_to_mobile_page(
        self,
        username: str,
        discard_pk: int,
        paper_number: int,
        *,
        question_idx_list: list,
    ):
        try:
            ManageDiscardService().reassign_discard_page_to_mobile_page_cmd(
                username, discard_pk, paper_number, question_idx_list
            )
        except ValueError as e:
            raise CommandError(e)

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="The user performing this operation"
        )
        parser.add_argument(
            "discard_pk", type=int, help="The pk of the discard page being assigned"
        )
        parser.add_argument(
            "-n",
            "--paper",
            type=int,
            help="The paper number to which the discard is to be assigned",
        )
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "-p",
            "--page",
            type=int,
            help="""
                The page number to which the discarded page is assigned (as a fixed page).
                You cannot specify both this and --question.
            """,
        )
        grp.add_argument(
            "-q",
            "--question",
            nargs="?",
            metavar="N",
            help="""
                Which question(s) are answered on this page, by question index?
                You can pass a single integer, or a list like `[1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `all` which uploads
                the page to all questions (this is also the default).

                If you pass `dnm`, the page will be attached to the
                "do not mark" group, making it available to this paper
                but not generally marked.
            """,
        )

    def handle(self, *args, **options):
        if options["page"]:
            self.reassign_discard_page_to_fixed_page(
                options["username"],
                options["discard_pk"],
                paper_number=options["paper"],
                page_number=options["page"],
            )
        else:
            n_questions = SpecificationService.get_n_questions()
            question_idx_list = check_question_list(options["question"], n_questions)
            self.reassign_discard_page_to_mobile_page(
                options["username"],
                options["discard_pk"],
                paper_number=options["paper"],
                question_idx_list=question_idx_list,
            )
