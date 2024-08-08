# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from __future__ import annotations

from pathlib import Path
from tabulate import tabulate

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from Papers.services import SpecificationService
from plom.misc_utils import format_int_list_with_runs
from ...services import BuildPapersService


class Command(BaseCommand):
    help = "Allows user to build papers, download them and delete them."

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "--start",
            type=int,
            metavar="N",
            help="Start building a PDF file for a specific paper",
        )
        grp.add_argument(
            "--start-all",
            action="store_true",
            help="Start building all PDF files for all papers that need it",
        )
        grp.add_argument(
            "--status",
            action="store_true",
            help="Show status of all PDF paper build chores",
        )
        grp.add_argument(
            "--count-done",
            action="store_true",
            help="Count number of completed PDF build chores",
        )
        grp.add_argument(
            "--list",
            action="store_true",
            help="List each paper PDF build chore and its status",
        )
        grp.add_argument(
            "--delete-all",
            action="store_true",
            help="Delete all PDFs that have been built",
        )
        grp.add_argument(
            "--cancel-all",
            action="store_true",
            help="Cancel any incomplete but queued PDF build chores",
        )
        grp.add_argument(
            "--download",
            type=int,
            metavar="N",
            help="Download a specific paper as a PDF file",
        )
        grp.add_argument(
            "--download-all",
            action="store_true",
            help="Download all papers in a ZIP file",
        )

    def start_all_tasks(self) -> None:
        bp_service = BuildPapersService()
        if bp_service.get_n_papers() == 0:
            self.stdout.write(
                "There are no papers to start. Check that DB is populated?"
            )
            return

        try:
            N = bp_service.send_all_tasks()
        except ValueError as e:
            raise CommandError(e) from e
        self.stdout.write(f"Started building {N} papers.")

    def start_specific_task(self, paper_number: int) -> None:
        bp_service = BuildPapersService()

        try:
            bp_service.send_single_task(paper_number)
        except (ValueError, ObjectDoesNotExist) as e:
            raise CommandError(e) from e
        self.stdout.write(f"Started building paper number {paper_number}.")

    def show_done_count(self) -> None:
        bp_service = BuildPapersService()
        if bp_service.are_all_papers_built():
            self.stdout.write("All complete")
        else:
            n = bp_service.get_n_complete_tasks()
            N = bp_service.get_n_tasks()
            self.stdout.write(f"Completed {n} / {N}")

    def show_task_status(self) -> None:
        bp_service = BuildPapersService()
        if bp_service.are_all_papers_built():
            self.stdout.write("All papers are now built")
        else:
            self.stdout.write("Not all papers are built")
        stats = bp_service.get_all_task_status()
        if not stats:
            self.stdout.write("No current chores.")
        else:
            self.stdout.write(f"{len(stats)} chores total:")
            rev_stat: dict[str, list[int]] = {}
            for n, state in stats.items():
                rev_stat.setdefault(state, []).append(n)
            for state, papers in rev_stat.items():
                lst = format_int_list_with_runs(papers, zero_padding=4)
                self.stdout.write(f' * "{state}": {lst}')
        N = bp_service.get_n_obsolete_tasks()
        print(f"There are also {N} obsolete PDF building chores")
        print("(left-over from previous runs, etc; don't worry about these)")

    def list_tasks(self) -> None:
        bp_service = BuildPapersService()
        tab = bp_service.get_task_context(include_obsolete=True)
        self.stdout.write(tabulate(tab, headers="keys", tablefmt="simple_outline"))

    def delete_all_tasks(self) -> None:
        self.stdout.write("Deleting all PDF building chores and associated PDFs...")
        bp_service = BuildPapersService()
        bp_service.reset_all_tasks()
        self.stdout.write("Deletion complete")

    def cancel_all_tasks(self) -> None:
        bp_service = BuildPapersService()
        N = bp_service.try_to_cancel_all_queued_tasks()
        self.stdout.write(f"Revoked {N} build paper PDF chores")

    def download_specific_paper(self, paper_number: int) -> None:
        bp_service = BuildPapersService()
        try:
            (name, b) = bp_service.get_paper_recommended_name_and_bytes(paper_number)
        except ValueError as err:
            raise CommandError(err)

        with open(Path(name), "wb") as fh:
            fh.write(b)
        self.stdout.write(f'Saved paper {paper_number} as "{name}"')

    def download_all_papers(self) -> None:
        bps = BuildPapersService()
        short_name = SpecificationService.get_short_name_slug()
        zgen = bps.get_zipfly_generator(short_name)
        with open(f"{short_name}.zip", "wb") as fh:
            self.stdout.write(f"Opening {short_name}.zip to write the zip-file")
            tot_size = 0
            for index, chunk in enumerate(zgen):
                tot_size += len(chunk)
                fh.write(chunk)
                self.stdout.write(
                    f"# chunk {index} = {tot_size // (1024 * 1024)}mb", ending="\r"
                )
        self.stdout.write(f'\nAll built papers saved in zip = "{short_name}.zip"')

    def handle(self, *args, **options) -> None:
        if options["start"]:
            self.start_specific_task(options["start"])
        elif options["download"]:
            self.download_specific_paper(options["download"])
        elif options["download_all"]:
            self.download_all_papers()
        elif options["start_all"]:
            self.start_all_tasks()
        elif options["delete_all"]:
            self.delete_all_tasks()
        elif options["cancel_all"]:
            self.cancel_all_tasks()
        elif options["count_done"]:
            self.show_done_count()
        elif options["status"]:
            self.show_task_status()
        elif options["list"]:
            self.list_tasks()
        else:
            self.print_help("manage.py", "plom_build_paper_pdfs")
