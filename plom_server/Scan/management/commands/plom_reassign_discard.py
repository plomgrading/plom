# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from plom.scan.question_list_utils import check_question_list
from Papers.services import SpecificationService
from ...services import ManageDiscardService


class Command(BaseCommand):
    """Reassign discarded pages.

    Examples:
        python3 manage.py plom_reassign_discard (username) (discardpage pk) -n paper_number -p page_number.
        python3 manage.py plom_reassign_discard (username) (discardpage pk) -n paper_number -q question_index.
    """

    help = "Reassign a (pushed) discarded page as a given fixed or mobile page."

    def reassign_discard_page(
        self,
        username: str,
        discard_pk: int,
        paper_number: int,
        *,
        page_number: int | None = None,
        question_list: list | None = None,
        really_do_it: bool = False,
    ):
        mds = ManageDiscardService()
        try:
            if page_number:
                mds.reassign_discard_page_to_fixed_page_cmd(
                    username, discard_pk, paper_number, page_number
                )
            elif question_list:
                mds.reassign_discard_page_to_mobile_page_cmd(
                    username, discard_pk, paper_number, question_list
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
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="By default this command does a dry-run of the discard. Add this flag to actually do the discard.",
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
                Which question(s) are answered on this page?
                You can pass a single integer, or a list like `[1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `all` which uploads
                the page to all questions (this is also the default).
            """,
        )

    def handle(self, *args, **options):
        if options["question"]:
            n_questions = SpecificationService.get_n_questions()
            question_list = check_question_list(options["question"], n_questions)
        else:
            question_list = []

        self.reassign_discard_page(
            options["username"],
            options["discard_pk"],
            paper_number=options["paper"],
            page_number=options["page"],
            question_list=question_list,
            really_do_it=options["yes"],
        )
