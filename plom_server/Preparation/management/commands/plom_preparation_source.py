# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from plom_server.Papers.services import SpecificationService

from ...services import SourceService, PapersPrinted


DeprecationNotice = """DEPRECATION NOTICE: plom_preparation_source (Issue #3981).
    Consider using plom-cli subcommands to manipulate sources.
    This suite of Django management commands is no longer being maintained."""


class Command(BaseCommand):
    help = "Displays the uploaded source pdfs and allows users to upload/download/remove source pdfs."

    def check_duplicates(self):
        duplicates = SourceService.check_pdf_duplication()
        if duplicates:
            self.stderr.write("There appear to be duplicate source pdfs on the server:")
            for sha, versions in duplicates.items():
                self.stderr.write(f"\tVersions {versions} have sha256 {sha}")

    def show_status(self):
        vup = SourceService.how_many_source_versions_uploaded()
        if vup:
            self.stdout.write(f"{vup} source pdf(s) uploaded.")
        else:
            self.stdout.write("No source pdfs uploaded.")
        src_list = SourceService.get_list_of_sources()
        for src in src_list:
            if src["uploaded"]:
                self.stdout.write(
                    f"Version {src['version']} - pdf with sha256:{src['hash']}"
                )
            else:
                self.stdout.write(f"Version {src['version']} - no pdf uploaded")
        # Now report any duplicated hashes
        self.check_duplicates()

    def copy_source_into_place(self, version, pdf_file_bytes):
        self.stdout.write(f"Downloading version {version} to 'source{version}.pdf'")
        save_path = Path(f"source{version}.pdf")
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

    def download_source(self, version: int | None = None, all: bool = False) -> None:
        src_list = SourceService.get_list_of_sources()
        up_list = [x for x in src_list if x["uploaded"]]
        if len(up_list) == 0:
            self.stdout.write("There are no source PDFs on the server.")
            return

        if all:
            if version is not None:
                raise CommandError("Cannot specify 'all' and 'version'")
            self.stdout.write("Downloading all versions on the server.")
            for src in up_list:
                v = src["version"]
                self.copy_source_into_place(v, SourceService.get_source_as_bytes(v))
            return

        if version in [x["version"] for x in up_list]:
            self.copy_source_into_place(
                version, SourceService.get_source_as_bytes(version)
            )
        else:
            raise CommandError(f"Source PDF version {version} is not on the server.")

    def remove_source(self, version: int | None = None, all: bool = False) -> None:
        if PapersPrinted.have_papers_been_printed():
            raise CommandError(
                "Papers have been printed. You cannot change the sources."
            )

        src_list = SourceService.get_list_of_sources()
        up_list = [x for x in src_list if x["uploaded"]]
        if len(up_list) == 0:
            self.stdout.write("There are no source PDFs on the server.")
            return

        if all:
            if version is not None:
                raise CommandError("Cannot specify 'all' and 'version'")
            self.stdout.write(f"Removing all {len(up_list)} source PDFs on server.")
            SourceService.delete_all_source_pdfs()
            return
        if version in [x["version"] for x in up_list]:
            assert isinstance(version, int)  # MyPy was worried
            SourceService.delete_source_pdf(version)
            self.stdout.write(f"Removed source PDF version {version} from server.")
        else:
            raise CommandError(f"Source PDF version {version} is not on the server.")

    def upload_source(self, version=None, source_pdf=None):
        if PapersPrinted.have_papers_been_printed():
            raise CommandError(
                "Papers have been printed. You cannot change the source PDFs."
            )

        if not SpecificationService.is_there_a_spec():
            raise CommandError(
                "There is not a valid specification on the server. Cannot upload."
            )

        src_list = SourceService.get_list_of_sources()
        version_list = [x["version"] for x in src_list]
        if version not in version_list:
            raise CommandError(
                f"Version {version} is invalid - must be one of {version_list}"
            )

        (existing_src,) = [x for x in src_list if x["version"] == version]
        if existing_src["uploaded"]:
            raise CommandError(
                f"Version {version} already on server with sha256 {existing_src['hash']}."
                "  Delete or upload to a different version."
            )

        source_path = Path(source_pdf)
        if not source_path.exists():
            raise CommandError(f"Cannot open file {source_path}.")

        # send the PDF
        # we should not be able to upload unless we have a spec
        with open(source_path, "rb") as fh:
            # TODO: confused by the type of fh: here we have a plain
            # file handle but the function talks about "in memory file"...
            success, msg = SourceService.take_source_from_upload(version, fh)
            if success:
                self.stdout.write(
                    f"Upload of source PDF for version {version} succeeded."
                )
            else:
                self.stderr.write(
                    f"Upload of source PDF for version {version} failed: {msg}"
                )
                return

        # check for any duplicates
        self.check_duplicates()

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting source PDFs.",
        )
        sub.add_parser("status", help="Show which sources have been uploaded")
        sp_U = sub.add_parser("upload", help="Upload a source PDF")
        sp_D = sub.add_parser("download", help="Download a source PDF")
        sp_R = sub.add_parser("remove", help="Remove a source PDF")

        sp_U.add_argument("source_pdf", type=str, help="The source PDF to upload")
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
        self.stdout.write(DeprecationNotice)
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
            self.print_help("manage.py", "plom_preparation_source")
