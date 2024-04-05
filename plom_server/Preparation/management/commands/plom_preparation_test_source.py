# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from Papers.services import SpecificationService

from ...services import SourceService, TestSourceService, PapersPrinted


class Command(BaseCommand):
    help = "Displays the uploaded test source pdfs and allows users to upload/download/remove test source pdfs."

    def check_duplicates(self):
        tss = TestSourceService()
        duplicates = tss.check_pdf_duplication()
        if duplicates:
            self.stderr.write("There appear to be duplicate source pdfs on the server:")
            for sha, versions in duplicates.items():
                self.stderr.write(f"\tVersions {versions} have sha256 {sha}")

    def show_status(self):
        tss = TestSourceService()
        vup = tss.how_many_test_versions_uploaded()
        if vup:
            self.stdout.write(f"{vup} test source pdf(s) uploaded.")
        else:
            self.stdout.write("No test source pdfs uploaded.")
        up_list = tss.get_list_of_sources()
        for v, source in up_list.items():
            if source:  # source = None or (internal filepath, sha256)
                self.stdout.write(f"Version {v} - pdf with sha256:{source[1]}")
            else:
                self.stdout.write(f"Version {v} - no pdf uploaded")
        # Now report any duplicated hashes
        self.check_duplicates()

    def copy_source_into_place(self, version, pdf_file_bytes):
        self.stdout.write(
            f"Downloading version {version} to 'test_source.{version}.pdf'"
        )
        save_path = Path(f"test_source.{version}.pdf")
        if save_path.exists():
            self.stdout.write(f"A file exists at {save_path} - overwrite it? [y/N]")
            choice = input().lower()
            if choice != "y":
                self.stdout.write("Skipping this file.")
                return
            else:
                self.stdout.write(f"Overwriting {save_path}.")

        with open(save_path, "wb") as fh:
            fh.write(pdf_file_bytes)

    def download_source(self, version=None, all=False):
        tss = TestSourceService()
        up_list = tss.get_list_of_uploaded_sources()
        if len(up_list) == 0:
            self.stdout.write("There are no test sources on the server.")
            return

        if all:
            self.stdout.write("Downloading all versions on the server.")
            for v, source in up_list.items():
                self.copy_source_into_place(v, tss.get_source_as_bytes(v))
            return

        if version in up_list:
            self.copy_source_into_place(version, tss.get_source_as_bytes(version))
        else:
            self.stderr.write(
                f"Test pdf source Version {version} is not on the server."
            )

    def remove_source(self, version=None, all=False):
        if PapersPrinted.have_papers_been_printed():
            raise CommandError(
                "Papers have been printed. You cannot change the sources."
            )

        tss = TestSourceService()
        up_list = tss.get_list_of_uploaded_sources()
        if len(up_list) == 0:
            self.stdout.write("There are no test sources on the server.")
            return

        if all:
            self.stdout.write(
                f"Removing all {len(up_list)} test source pdfs on server."
            )
            tss.delete_all_test_sources()
            return
        if version in up_list:
            tss.delete_test_source(version)
            self.stdout.write(
                f"Removing test pdf source version {version} from server."
            )
        else:
            self.stderr.write(
                f"Test pdf source Version {version} is not on the server."
            )

    def upload_source(self, version=None, source_pdf=None):
        if PapersPrinted.have_papers_been_printed():
            raise CommandError(
                "Papers have been printed. You cannot change the sources."
            )

        if not SpecificationService.is_there_a_spec():
            raise CommandError(
                "There is not a valid test specification on the server. Cannot upload."
            )

        tss = TestSourceService()
        src_list = tss.get_list_of_sources()
        if version not in src_list:
            version_list = sorted(list(src_list.keys()))
            raise CommandError(
                f"Version {version} is invalid - must be one of {version_list}"
            )

        existing_src = src_list[version]
        if existing_src is not None:
            raise CommandError(
                f"Version {version} already on server with sha256 = {existing_src[1]}. Delete or upload to a different version."
            )

        source_path = Path(source_pdf)
        if not source_path.exists():
            raise CommandError(f"Cannot open file {source_path}.")

        # send the PDF
        # we should not be able to upload unless we have a spec
        with open(source_path, "rb") as fh:
            # TODO: confused by the type of fh: here we have a plain
            # file handle but the function talks about "in memory file"...
            success, msg = SourceService.take_source_from_upload(
                version, SpecificationService.get_n_pages(), fh
            )
            if success:
                self.stdout.write(
                    f"Upload of source pdf for version {version} succeeded."
                )
            else:
                self.stderr.write(
                    f"Upload of source pdf for version {version} failed = {msg}"
                )
                return

        # check for any duplicates
        self.check_duplicates()

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting test source pdfs.",
        )
        sub.add_parser("status", help="Show which sources have been uploaded")
        sp_U = sub.add_parser("upload", help="Upload a test source pdf")
        sp_D = sub.add_parser("download", help="Download a test source pdf")
        sp_R = sub.add_parser("remove", help="Remove a test source pdf")

        sp_U.add_argument("source_pdf", type=str, help="The source pdf to upload")
        sp_U.add_argument(
            "-v", "--version", type=int, help="The version to upload", required=True
        )

        grp_D = sp_D.add_mutually_exclusive_group(required=True)
        grp_D.add_argument("-v", "--version", type=int, help="The version to download")
        grp_D.add_argument(
            "-a", "--all", action="store_true", help="Download all versions"
        )

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
                version=options["version"], source_pdf=options["source_pdf"]
            )
        elif options["command"] == "download":
            self.download_source(version=options["version"], all=options["all"])
        elif options["command"] == "remove":
            self.remove_source(version=options["version"], all=options["all"])
        else:
            self.print_help("manage.py", "plom_preparation_test_source")
