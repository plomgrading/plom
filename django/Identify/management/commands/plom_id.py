# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from Identify.services.id_reader import IDReaderService


class Command(BaseCommand):
    """Management command for extracting the ID box.

    python3 manage.py plom_id (top) (bottom) (left) (right)
    """

    help = "Extract the ID box from all papers."

    def get_id_box(self, top, bottom, left, right):
        idservice = IDReaderService()
        box = (top, bottom, left, right)
        if any(x is None for x in box):
            if all(x is None for x in box):
                box = None
            else:
                raise CommandError("If you provide one dimension you must provide all")
        try:
            idservice.get_id_box_cmd(box)
            self.stdout.write("Extracted the ID box from all known ID pages.")
        except ValueError as err:
            raise CommandError(err)

    def add_arguments(self, parser):
        parser.add_argument(
            "top",
            type=float,
            help="top bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "bottom",
            type=float,
            help="bottom bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "left",
            type=float,
            help="left bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "right",
            type=float,
            help="right bound of rectangle to extract",
            default=None,
            nargs="?",
        )

    def handle(self, *args, **options):
        self.get_id_box(
            options["top"], options["bottom"], options["left"], options["right"]
        )
