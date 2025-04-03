# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom_server.Papers.services import PaperInfoService
from ...services import RectangleExtractor


class Command(BaseCommand):
    """Command to extract a rectangle from all papers with given page/version.

    python3 manage.py plom_extract_rectangle ...
    """

    help = "Extract the rectangle from the given page/version of each paper."

    def extract_rectangle(
        self, version: int, page: int, rectangle: dict[str, float]
    ) -> None:
        # make a directory into which we extract stuff
        er_dir = Path("./extracted")
        er_dir.mkdir(exist_ok=True)

        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            page, version=version, scanned=True
        )
        self.stdout.write(
            f"Extracting version {version} page {page} from papers {paper_numbers}"
        )
        try:
            rex = RectangleExtractor(version, page)
        except ValueError as err:
            raise CommandError(err)

        for pn in paper_numbers:
            fname = er_dir / f"ex_rect_v{version}_pg{page}_{pn}.png"
            rect_region_bytes = rex.extract_rect_region(
                pn,
                rectangle["left"],
                rectangle["top"],
                rectangle["right"],
                rectangle["bottom"],
            )
            if rect_region_bytes is None:
                self.stdout.write(f"Skipping papernum {pn}: rex could not extract")
                continue
            fname.write_bytes(rect_region_bytes)

        self.stdout.write(f'Action completed, files written to directory "{er_dir}"')

    def add_arguments(self, parser):
        parser.add_argument(
            "--ver",
            type=int,
            help="The version of the pages from which to extract.",
            required=True,
        )
        parser.add_argument(
            "--pg",
            type=int,
            help="The page from which to extract",
            required=True,
        )
        parser.add_argument("--left", type=float, required=True)
        parser.add_argument("--top", type=float, required=True)

        parser.add_argument("--right", type=float, required=True)

        parser.add_argument("--bottom", type=float, required=True)

    def handle(self, *args, **options):
        rectangle = {
            "left": options["left"],
            "right": options["right"],
            "top": options["top"],
            "bottom": options["bottom"],
        }
        self.extract_rectangle(
            version=options["ver"], page=options["pg"], rectangle=rectangle
        )
