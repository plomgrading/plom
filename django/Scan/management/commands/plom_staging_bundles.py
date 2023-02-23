# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

import pathlib
import hashlib
import fitz
from datetime import datetime
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
        
        with open(source_pdf, "rb") as f:
            file_bytes = f.read()
            pdf_doc = fitz.open(stream=file_bytes)
            filename_stem = pathlib.Path(str(f)).stem
            slug = slugify(filename_stem)
            timestamp = datetime.timestamp(timezone.now())
            hashed = hashlib.sha256(file_bytes).hexdigest()

        scanner.upload_bundle_cmd(pdf_doc, slug, username, timestamp, hashed)

    def add_arguments(self, parser):
        sp = parser.add_subparsers(
            dest="command",
            description="Upload PDF files.",
        )

        sp_upload = sp.add_parser("upload", help="Upload a test pdf.")
        sp_upload.add_argument("username", type=str, help="Which username to upload as.")
        sp_upload.add_argument("source_pdf", type=str, help="The test pdf to upload.")

    def handle(self, *args, **options):
        if options["command"] == "upload":
            self.upload_pdf(username = options["username"], source_pdf=options["source_pdf"])
        else:
            self.print_help("manage.py", "plom_staging_bundles")
        
