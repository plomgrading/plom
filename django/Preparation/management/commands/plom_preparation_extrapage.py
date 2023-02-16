from django.core.management.base import BaseCommand, CommandError

from Preparation.services import ExtraPageService

from pathlib import Path
import shutil


class Command(BaseCommand):
    help = (
        "Allows user to enqueue building of the extra page pdf, download or delete it."
    )

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "--build",
            action="store_true",
            help="Queue the building of the extra page pdf",
        )
        grp.add_argument(
            "--delete", action="store_true", help="Delete the extra page pdf"
        )
        grp.add_argument(
            "--download",
            const="extra_page.pdf",
            nargs="?",
            type=str,
            help="Download the extra page pdf",
        )

    def build_extra_page(self):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "todo":
            ep_service.build_extra_page_pdf()
            self.stdout.write("Enqueued extra page pdf build")
        elif current_state == "complete":
            self.stdout.write("Extra page pdf has already been built")
        else:
            self.stdout.write(
                f"Extra page pdf build task has already been queued = {current_state}"
            )

    def delete_extra_page(self):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "complete":
            ep_service.delete_extra_page_pdf()
            self.stdout.write("Deleting extra page pdf")
        else:
            self.stdout.write(f"Extra page has not yet been built = {current_state}")

    def download_extra_page(self, destination):
        ep_service = ExtraPageService()
        current_state = ep_service.get_extra_page_task_status()
        if current_state == "complete":
            self.stdout.write(f"Downloading extra page pdf to {destination}")
            with Path(destination).open("wb") as fh:
                fh.write(ep_service.get_extra_page_pdf_as_bytes())
        else:
            self.stdout.write(f"Extra page has not yet been built = {current_state}")

    def handle(self, *args, **options):
        if options["build"]:
            self.build_extra_page()

        elif options["delete"]:
            self.delete_extra_page()

        elif options["download"]:
            self.download_extra_page(options["download"])
        else:
            ep_service = ExtraPageService()
            current_state = ep_service.get_extra_page_task_status()
            self.stdout.write(f"Extra page build task is {current_state}")
