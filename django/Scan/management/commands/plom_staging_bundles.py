# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    """
    commands:
        python3 manage.py plom_staging_bundles upload (username) (file) <- drag and drop or copy path
        python3 manage.py plom_staging_bundles status
    """
    help = "Upload bundle pdf files to staging area"
    
    def upload_pdf(self, username=None, source_pdf=None):
        temp_username = User.objects.filter(username__iexact=username).values()
        # False
        if not temp_username.exists():
            return self.stdout.write(f"{username} does not exist!")
        
        # True
        self.stdout.write(f"this is the username {temp_username[0]['username']}")
        self.stdout.write(f"this is the source path {source_pdf}.")

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
        
