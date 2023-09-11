# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.management.base import BaseCommand

from Identify.services import IDHomeworkService


class Command(BaseCommand):
    """python3 manage.py plom_id_homework username paper_number sid sname ."""

    def identify_homework(
        self,
        username: str,
        paper_number: int,
        student_id: str,
        student_name: str,
    ):
        IDHomeworkService().identify_homework_cmd(
            username, paper_number, student_id, student_name
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="The user performing this operation"
        )
        parser.add_argument(
            "paper",
            type=int,
            help="The paper number to which the homework has been uploaded and to which we assign the ID.",
        )
        parser.add_argument(
            "student_id",
            type=str,
            help="The id of the student who submitted the homework.",
        )
        parser.add_argument(
            "student_name",
            type=str,
            help="The name of the student who submitted the homework.",
        )

    def handle(self, *args, **options):
        self.identify_homework(
            username=options["username"],
            paper_number=options["paper"],
            student_id=options["student_id"],
            student_name=options["student_name"],
        )
