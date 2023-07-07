# Copyright (C) 2023 Brennen Chiu

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from Identify.services import IDService


class Command(BaseCommand):
    """Command tool for clearing certain ID paper number or all ID papers.

    python manage.py clear_id (paper_num)
    python manage.py clear_id all
    """

    help = "Clear the ID of a specific paper or clear all IDs.\
            To clear all IDs: python manage.py clear_id all\
            To clear a specific ID: python manage.py clear_id (paper number)"

    def specific_id(self, paper_num):
        try:
            IDService().set_id__task_todo_and_clear_specific_id_cmd(paper_num)
            self.stdout.write(f"Cleared ID for paper number #{paper_num}")
        except ObjectDoesNotExist:
            raise CommandError(
                f"Cannot clear ID due to paper number #{paper_num} has yet to be identified."
            )

    def clear_all_ids(self):
        try:
            IDService().set_all_id__task_todo_and_clear_all_id_cmd()
            self.stdout.write("All IDs cleared.")
        except ObjectDoesNotExist as err:
            raise CommandError(err)

    def add_arguments(self, parser):
        parser.add_argument("paper_num", type=str, help="")

    def handle(self, *args, **options):
        if options["paper_num"].isnumeric():
            self.specific_id(options["paper_num"])
        elif options["paper_num"] == "all":
            self.clear_all_ids()
        else:
            self.print_help("manage.py", "clear_id")
