# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

import sys
from pathlib import Path
from time import sleep

from tabulate import tabulate
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from Papers.services import PaperInfoService, SpecificationService

from ...services import ReassembleService


class Command(BaseCommand):
    """Generate reassembled papers with TA annotations from the command line."""

    help = "Queue the creation of PDFs to return to students."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait",
            action="store_true",
            help="Wait for queued reassembly to finish",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="""
                Show status of all papers w.r.t. reassembly.
                If any errors have occurred, exit with non-zero
                status.
            """,
        )
        parser.add_argument(
            "--papernum",
            type=int,
            nargs="?",
            help="Queue the reassembly of this one particular paper number.",
        )
        parser.add_argument(
            "--zip",
            type=Path,
            nargs="?",
            help="Download all the reassembled papers to the specified zip file",
        )
        parser.add_argument(
            "--delete-all",
            action="store_true",
            help="""
                Delete all reasssembled PDFs that have been built
                on the server.  Actually we don't delete, just mark
                as obsolete.
            """,
        )
        parser.add_argument(
            "--cancel-all",
            action="store_true",
            help="Cancel any incomplete but queued PDF reassembly chores",
        )

    def reassemble_one_paper(self, paper_num: int) -> None:
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")
        try:
            ReassembleService().queue_single_paper_reassembly(paper_num)
        except ValueError as e:
            raise CommandError(e)
        self.stdout.write("Queued reassembly of paper num {paper_num}")

    def reassemble_all_papers(self) -> None:
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")
        ReassembleService().queue_all_paper_reassembly()
        self.stdout.write("Queued reassembly of all papers and reports")

    def download_zip(self, zip_path):
        short_name = slugify(SpecificationService.get_shortname())
        zipper = ReassembleService().get_zipfly_generator(short_name)
        if zip_path.exists():
            raise CommandError(f"File '{zip_path}' already exists.")
        with zip_path.open("wb") as fh:
            for chunk in zipper:
                fh.write(chunk)

    def show_status(self) -> bool:
        any_errors = False
        reas = ReassembleService()
        tab = reas.get_all_paper_status_for_reassembly()
        for row in tab:
            # keep the humanized ones
            row.pop("last_update")
            row.pop("reassembled_time")
            if row["reassembled_status"] == "Error":
                any_errors = True
        self.stdout.write(tabulate(tab, headers="keys", tablefmt="simple_outline"))
        if any_errors:
            self.stdout.write("One or more reassembly tasks has failed!")
        return any_errors

    def wait_for_chores(self) -> None:
        reas = ReassembleService()
        while True:
            mid_reassembly = reas.how_many_papers_are_mid_reassembly()
            if mid_reassembly > 0:
                self.stdout.write(
                    f"Still {mid_reassembly} papers being reassembled - waiting."
                )
                sleep(2)
            else:
                break
        self.stdout.write("No active reassembly tasks.")

    def delete_all_chores(self):
        service = ReassembleService()
        service.reset_all_paper_reassembly()

    def cancel_all_tasks(self):
        service = ReassembleService()
        N = service.try_to_cancel_all_queued_chores()
        self.stdout.write(f"Revoked {N} reassemble PDF chores")

    def handle(self, *args, **options):
        paper_num = options["papernum"]
        zip_path = options["zip"]
        if options["status"]:
            r = self.show_status()
            if r:
                # TODO: not sure if proper: only thing I found about return codes
                # is this WONTFIX bug https://code.djangoproject.com/ticket/25419
                sys.exit(1)
        elif options["wait"]:
            self.wait_for_chores()
        elif options["delete_all"]:
            self.delete_all_chores()
        elif options["cancel_all"]:
            self.cancel_all_tasks()
        elif zip_path:
            self.stdout.write("Downloading zip of reassembled papers")
            self.download_zip(Path(zip_path))
        elif paper_num:
            self.stdout.write(f"Reassembling paper {paper_num}...")
            self.reassemble_one_paper(paper_num)
        else:
            self.stdout.write("Reassembling all papers...")
            self.reassemble_all_papers()
