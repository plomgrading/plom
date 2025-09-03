# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from tabulate import tabulate

from django.core.management.base import BaseCommand, CommandError

from ...services import ManageScanService


class Command(BaseCommand):
    """python3 manage.py plom_list_images_in_paper (paper_number)."""

    help = "List the images in the given paper"

    def list_images_in_paper(self, paper_number: int):
        mss = ManageScanService()
        try:
            page_image_list = mss.get_page_images_in_paper(paper_number)
        except ValueError as e:
            raise CommandError(e)
        headers = ["page_type", "page_number", "question_idx", "page_pk", "image_pk"]
        out_list = []
        for pi in page_image_list:
            if pi["image"] is None:
                pi["image"] = "no image"
            if pi["page_type"] == "fixed":
                out_list.append(
                    [
                        pi["page_type"],
                        pi["page_number"],
                        pi["question_index"],
                        pi["page_pk"],
                        pi["image"],
                    ]
                )
            else:
                out_list.append(
                    [
                        pi["page_type"],
                        "",
                        pi["question_index"],
                        pi["page_pk"],
                        pi["image"],
                    ]
                )

        self.stdout.write(
            tabulate(out_list, headers=headers, tablefmt="simple_outline")
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "paper_number",
            type=int,
            help="List the images in the paper with this paper number",
        )

    def handle(self, *args, **options):
        self.list_images_in_paper(
            options["paper_number"],
        )
