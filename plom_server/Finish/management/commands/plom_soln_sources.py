# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

import pymupdf as fitz
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom_server.Papers.services import SpecificationService, SolnSpecService
from ...services import SolnSourceService


class Command(BaseCommand):
    help = "Displays the uploaded solution pdfs and allows users to upload/download/remove solution pdfs."

    def show_status(self):
        soln_hash = SolnSourceService().get_solution_pdf_hashes()
        for v, h in soln_hash.items():
            self.stdout.write(f"Version {v}: {h}")

    def upload_source(self, version: int, source_pdf_path: str) -> None:
        versions = SpecificationService.get_list_of_versions()
        if version not in versions:
            self.stderr.write(
                f"Version {version} is out of range - must be in {versions}."
            )
            return

        pdf_path = Path(source_pdf_path)

        if not pdf_path.exists():
            self.stderr.write(f"Cannot open {source_pdf_path}.")
            return

        # make sure we can actually open the pdf and check pages
        np = SolnSpecService.get_n_pages()
        try:
            with fitz.open(pdf_path) as doc:
                if len(doc) != np:
                    raise CommandError(
                        f"Solution source pdf must have {np} pages according to"
                        f"the soln spec; supplied file has {len(doc)} pages."
                    )
        except fitz.FileDataError as err:
            raise CommandError(err)

        try:
            with pdf_path.open("rb") as fh:
                SolnSourceService().take_solution_source_pdf_from_upload(version, fh)
        except ValueError as err:
            raise CommandError(err)

    def remove_source(self, version=None, all=False):
        try:
            if all:
                SolnSourceService().remove_all_solution_pdf()
            elif version:
                SolnSourceService().remove_solution_pdf(version)
            else:
                return
        except ValueError as err:
            raise CommandError(err)

    def download_source(self, version):
        try:
            soln_pdf_bytes = (
                SolnSourceService().get_soln_pdf_for_download(version).read()
            )
        except ValueError as err:
            raise CommandError(err)
        fname = f"solution{version}.pdf"
        with open(fname, "wb") as fh:
            fh.write(soln_pdf_bytes)
        self.stdout.write(
            f"Wrote solution source pdf for version {version} to {fname}."
        )

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting solution pdfs.",
        )
        sub.add_parser("status", help="Show which sources have been uploaded")
        sp_U = sub.add_parser("upload", help="Upload a solution pdf")
        sp_D = sub.add_parser("download", help="Download a solution pdf")
        sp_R = sub.add_parser("remove", help="Remove a solution pdf")

        sp_U.add_argument("source_pdf", type=str, help="The source pdf to upload")
        sp_U.add_argument(
            "-v", "--version", type=int, help="The version to upload", required=True
        )

        grp_D = sp_D.add_mutually_exclusive_group(required=True)
        grp_D.add_argument("-v", "--version", type=int, help="The version to download")

        grp_R = sp_R.add_mutually_exclusive_group(required=True)
        grp_R.add_argument("-v", "--version", type=int, help="The version to remove")
        grp_R.add_argument(
            "-a", "--all", action="store_true", help="Remove all versions"
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_source(
                version=options["version"], source_pdf_path=options["source_pdf"]
            )
        elif options["command"] == "download":
            self.download_source(version=options["version"])
        elif options["command"] == "remove":
            self.remove_source(version=options["version"], all=options["all"])
        else:
            self.print_help("manage.py", "plom_solution_sources")
