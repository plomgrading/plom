# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand

from ...services import ScrapPaperService


class Command(BaseCommand):
    help = (
        "Allows user to enqueue building of the scrap-paper pdf, download or delete it."
    )

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("build", help="Queue the building of the scrap-paper pdf")
        sub.add_parser("delete", help="Delete the scrap-paper pdf")
        sub_dwn = sub.add_parser("download", help="Download the scrap-paper pdf")
        sub_dwn.add_argument(
            "dest",
            default="scrap_paper.pdf",
            nargs="?",
            type=str,
        )

    def build_scrap_paper(self):
        sp_service = ScrapPaperService()
        current_state = sp_service.get_scrap_paper_task_status()
        if current_state == "To Do":
            sp_service.build_scrap_paper_pdf()
            self.stdout.write("Enqueued scrap-paper pdf build")
        elif current_state == "Complete":
            self.stdout.write("Scrap-paper pdf has already been built")
        else:
            self.stdout.write(
                f"Scrap-paper pdf build task has already been queued = {current_state}"
            )

    def delete_scrap_paper(self):
        sp_service = ScrapPaperService()
        current_state = sp_service.get_scrap_paper_task_status()
        if current_state in ["Error", "Complete"]:
            sp_service.delete_scrap_paper_pdf()
            self.stdout.write("Deleting scrap-paper pdf")
        else:
            self.stdout.write(f"Scrap-paper has not yet been built = {current_state}")

    def download_scrap_paper(self, destination):
        sp_service = ScrapPaperService()
        current_state = sp_service.get_scrap_paper_task_status()
        if current_state == "Complete":
            self.stdout.write(f"Downloading scrap-paper pdf to {destination}")
            with Path(destination).open("wb") as fh:
                fh.write(sp_service.get_scrap_paper_pdf_as_bytes())
        else:
            self.stdout.write(f"Scrap-paper has not yet been built = {current_state}")

    def handle(self, *args, **options):
        if options["command"] == "build":
            self.build_scrap_paper()

        elif options["command"] == "delete":
            self.delete_scrap_paper()

        elif options["command"] == "download":
            self.download_scrap_paper(options["dest"])
        else:
            sp_service = ScrapPaperService()
            current_state = sp_service.get_scrap_paper_task_status()
            self.stdout.write(f"Scrap-paper build task is {current_state}")
