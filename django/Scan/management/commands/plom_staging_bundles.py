# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from datetime import datetime
import fitz
import hashlib
import pathlib
from tabulate import tabulate

from django.utils import timezone
from django.utils.text import slugify
from django.core.management.base import BaseCommand

from Scan.services import ScanService


class Command(BaseCommand):
    """
    commands:
        python3 manage.py plom_staging_bundles upload (username) (file) <- drag and drop or copy path
        python3 manage.py plom_staging_bundles status
    """

    help = "Upload bundle pdf files to staging area"

    def upload_pdf(self, username=None, source_pdf=None):
        scanner = ScanService()

        if source_pdf is None:
            self.stderr.write("No bundle supplied. Stopping.")
            return

        with open(source_pdf, "rb") as f:
            file_bytes = f.read()

        pdf_doc = fitz.open(stream=file_bytes)
        filename_stem = pathlib.Path(source_pdf).stem
        slug = slugify(filename_stem)
        timestamp = datetime.timestamp(timezone.now())
        hashed = hashlib.sha256(file_bytes).hexdigest()

        if scanner.check_for_duplicate_hash(hashed):
            self.stderr.write("Upload failed - Bundle was already uploaded.")
            return

        try:
            scanner.upload_bundle_cmd(pdf_doc, slug, username, timestamp, hashed)
            self.stdout.write(f"Uploaded {source_pdf} as user {username} - processing it in the background now.")
        except ValueError as err:
            self.stderr.write(f"{err}")

    def staging_bundle_status(self):
        scanner = ScanService()
        bundle_status = scanner.staging_bundle_status_cmd()
        self.stdout.write(tabulate(bundle_status, headers="firstrow", tablefmt="simple_outline"))

        if len(bundle_status) == 1:
            self.stdout.write("No bundles uploaded.")

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="Upload PDF files.",
        )

        # Upload
        sp_upload = sp.add_parser("upload", help="Upload a test pdf.")
        sp_upload.add_argument(
            "username", type=str, help="Which username to upload as."
        )
        sp_upload.add_argument("source_pdf", type=str, help="The test pdf to upload.")

        # Status
        sp.add_parser("status", help="Show the status of the staging bundles.")

    def handle(self, *args, **options):
        if options["command"] == "upload":
            self.upload_pdf(
                username=options["username"], source_pdf=options["source_pdf"]
            )
        elif options["command"] == "status":
            self.staging_bundle_status()
        else:
            self.print_help("manage.py", "plom_staging_bundles")
