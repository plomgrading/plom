# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
import fitz

from Papers.services import SpecificationService
from SpecCreator.services import StagingSpecificationService, ReferencePDFService

from ...services import PQVMappingService


class Command(BaseCommand):
    help = "Displays the current status of the spec, and allows user to upload/download/remove."

    def show_status(self):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("No valid test spec present")
            return

        toml_text = SpecificationService.get_the_spec_as_toml()
        self.stdout.write("A valid test spec is present:")
        self.stdout.write("#" * 40)
        self.stdout.write(f"{toml_text}")
        self.stdout.write("#" * 40)

    def download_spec(self, dest=None):
        if not SpecificationService.is_there_a_spec():
            self.stderr.write("No valid test spec present")
            return

        spec_dict = SpecificationService.get_the_spec()
        self.stdout.write(
            f"A valid test spec is present: shortname {spec_dict['name']}"
        )
        if dest is None:
            fname = Path(slugify(spec_dict["name"]) + "_spec.toml")
        else:
            fname = Path(dest)
        self.stdout.write(f"Writing test spec toml to {fname}")
        if fname.exists():
            self.stderr.write(f"File {fname} already present - not overwriting.")
            return
        with open(fname, "w") as f:
            f.write(SpecificationService.get_the_spec_as_toml())

    @transaction.atomic
    def upload_spec(self, spec_file, pdf_file):
        if SpecificationService.is_there_a_spec():
            raise CommandError(
                "There is already a spec present. Cannot proceed with upload."
            )

        spec_path = Path(spec_file)
        if spec_path.exists() is False:
            self.stderr.write(f"Cannot open {spec_path}.")
            return
        try:
            with open(spec_path) as fh:
                spec_dict = tomllib.load(fh)
        except tomllib.TomlDecodeError as err:
            self.stderr.write(f"Cannot decode the toml file - {err}")
            return
        self.stdout.write(f"From {spec_path} read spec dict = {spec_dict}")

        pdf_path = Path(pdf_file)
        if pdf_path.exists() is False:
            self.stderr.write(f"Cannot open {pdf_path}.")
            return
        pdf_doc = fitz.Document(pdf_path)
        if pdf_doc.page_count != spec_dict["numberOfPages"]:
            self.stderr.write(
                f"Sample pdf does not match the test specification. PDF has {pdf_doc.page_count}, but spec indicates {spec_dict['numberOfPages']}."
            )
        with open(pdf_path, "rb") as f:
            pdf_doc_file = SimpleUploadedFile("spec_reference.pdf", f.read())
        self.stdout.write("Sample pdf has correct page count - matches specification.")

        reference = ReferencePDFService()
        reference.new_pdf(
            staging_spec, "spec_reference.pdf", pdf_doc.page_count, pdf_doc_file
        )

        try:
            SpecificationService.load_spec_from_toml(spec_path, True)
        except ValueError as err:
            self.stderr.write(f"There was an error validating the spec: {err}")
            return

        self.stdout.write("Test specification validated.")

        self.stdout.write("Test specification and sample pdf uploaded to server.")

    def remove_spec(self):
        pqvs = PQVMappingService()
        if pqvs.is_there_a_pqv_map():
            self.stderr.write("Warning - there is question-version mapping present.")
            self.stderr.write(
                "The test-spec cannot be deleted until that is removed; use the plom_preparation_qvmap command to remove the qv-mapping."
            )
            return
        staging_spec = StagingSpecificationService()
        self.stdout.write("Removing the test specification.")
        staging_spec.reset_specification()
        if SpecificationService.is_there_a_spec():
            SpecificationService.remove_spec()

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting of a classlist.",
        )
        sub.add_parser("status", help="Show details of current test spec")
        sp_U = sub.add_parser("upload", help="Upload a test spec")
        sp_D = sub.add_parser(
            "download", help="Download the current test spec (if is valid)"
        )
        sp_D.add_argument(
            "dest", type=str, nargs="?", help="Where to download the test spec toml"
        )
        sub.add_parser("remove", help="Remove the current test spec from the server")

        sp_U.add_argument(
            "test_spec_toml", type=str, help="The test spec toml to upload"
        )
        sp_U.add_argument("source_pdf", type=str, help="A source PDF of the test.")

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_spec(
                options["test_spec_toml"],
                options["source_pdf"],
            )
        elif options["command"] == "download":
            self.download_spec(options["dest"])
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_test_spec")
