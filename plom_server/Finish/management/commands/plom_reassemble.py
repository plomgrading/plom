# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from pathlib import Path
import sys

from tabulate import tabulate
from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from Finish.services import ReassembleService
from Papers.services import PaperInfoService, SpecificationService
from Papers.models import Paper


class Command(BaseCommand):
    """Generate reassembled test-papers with TA annotations from the command line."""

    help = "Create PDFs to return to students"

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
        # TODO: document that this is some local build, different
        # from the online list.  E.g., Chores and Huey are not used.
        parser.add_argument(
            "--testnum",
            type=int,
            nargs="?",
            help="Which test paper to reassemble (optional)",
        )
        parser.add_argument(
            "--save-path",
            type=Path,
            nargs="?",
            help="Path for saving reassembled papers (optional)",
        )
        parser.add_argument(
            "--zip",
            type=Path,
            nargs="?",
            help="Path for saving zip of reassembled papers (optional)",
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

    def reassemble_one_paper(self, test_num, save_path="reassembled"):
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")
        if not paper_service.is_this_paper_in_database(test_num):
            raise CommandError(f"Paper number {test_num} does not exist - stopping.")

        paper = Paper.objects.get(paper_number=test_num)
        reassembler = ReassembleService()

        try:
            out_path = reassembler.reassemble_paper(paper, outdir=save_path)
            self.stdout.write(f"File written to {out_path.absolute()}")
        except ValueError as e:
            raise CommandError(e)

    def reassemble_all_papers(self, save_path="reassembled"):
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
        save_path = options["save_path"]
        test_num = options["testnum"]
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
        elif test_num:
            self.stdout.write(f"Reassembling paper {test_num}...")
            self.reassemble_one_paper(test_num, save_path=save_path)
        else:
            self.stdout.write("Reassembling all papers...")
            self.reassemble_all_papers(save_path=save_path)
