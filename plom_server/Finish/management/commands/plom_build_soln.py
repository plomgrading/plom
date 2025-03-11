# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...services import BuildSolutionService


class Command(BaseCommand):
    """Build solutions for a specific paper."""

    def add_arguments(self, parser):
        parser.add_argument("paper", type=int)
        parser.add_argument(
            "-w",
            "--watermark",
            action="store_true",
            help="Watermark the solution with students id.",
        )
        parser.add_argument(
            "-d",
            "--directory",
            default="solutions",
            type=str,
            help="The directory in which to save the pdf.",
        )

    def handle(self, *args, **options):
        try:
            pdf_bytes, fname = BuildSolutionService().assemble_solution_for_paper(
                options["paper"], watermark=options["watermark"]
            )
        except ValueError as err:
            raise CommandError(err)

        dest_dir = Path(options["directory"])
        dest_dir.mkdir(exist_ok=True)
        f_path = dest_dir / fname

        with f_path.open("wb") as fh:
            fh.write(pdf_bytes)
