# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand

from ...services import ExtraPageService


class Command(BaseCommand):
    help = (
        "Allows user to enqueue building of the extra page pdf, download or delete it."
    )

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="command")
        sub_b = sub.add_parser("build", help="Queue the building of the extra page pdf")
        sub_del = sub.add_parser("delete", help="Delete the extra page pdf")
        sub_dwn = sub.add_parser("download", help="Download the extra page pdf")
        sub_dwn.add_argument(
            "dest",
            const="extra_page.pdf",
            nargs="?",
            type=str,
        )

    def build_extra_page(self):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "To Do":
            ep_service.build_extra_page_pdf()
            self.stdout.write("Enqueued extra page pdf build")
        elif current_state == "Complete":
            self.stdout.write("Extra page pdf has already been built")
        else:
            self.stdout.write(
                f"Extra page pdf build task has already been queued = {current_state}"
            )

    def delete_extra_page(self):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "Complete":
            ep_service.delete_extra_page_pdf()
            self.stdout.write("Deleting extra page pdf")
        else:
            self.stdout.write(f"Extra page has not yet been built = {current_state}")

    def download_extra_page(self, destination):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "Complete":
            self.stdout.write(f"Downloading extra page pdf to {destination}")
            with Path(destination).open("wb") as fh:
                fh.write(ep_service.get_extra_page_pdf_as_bytes())
        else:
            self.stdout.write(f"Extra page has not yet been built = {current_state}")

    def handle(self, *args, **options):
        if options["command"] == "build":
            self.build_extra_page()

        elif options["command"] == "delete":
            self.delete_extra_page()

        elif options["command"] == "download":
            self.download_extra_page(options["dest"])
        else:
            ep_service = ExtraPageService()
            current_state = ep_service.get_extra_page_task_status()
            self.stdout.write(f"Extra page build task is {current_state}")
