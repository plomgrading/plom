from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.core.files.uploadedfile import SimpleUploadedFile

from SpecCreator.services import StagingSpecificationService, ReferencePDFService
from Papers.services import SpecificationService
from Preparation.services import PQVMappingService
from plom import SpecVerifier

import copy
import fitz
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit


class Command(BaseCommand):
    help = "Displays the current status of the spec, and allows user to upload/download/remove."

    def show_status(self):
        speck = SpecificationService()
        spec_dict = speck.get_the_spec()
        toml_text = tomlkit.dump(spec_dict)

        if speck.is_there_a_spec():
            self.stdout.write("A valid test spec is present:")
            self.stdout.write("#" * 40)
            self.stdout.write(f"{toml_text}")
            self.stdout.write("#" * 40)
        else:
            self.stdout.write("No valid test spec present")

    def download_spec(self):
        speck = SpecificationService()
        spec_dict = speck.get_the_spec()

        if not speck.is_there_a_spec():
            self.stderr.write("No valid test spec present")
            return

        self.stdout.write(
            "A valid test spec is present - shortname = {spec_dict['name']}"
        )
        fname = Path(slugify(spec_dict["name"]) + "_spec.toml")
        self.stdout.write(f"Writing test spec toml to {fname}")
        if fname.exists():
            self.stderr.write(f"File {fname} already present - cannot overwrite.")
            return
        with open(fname, "w") as fh:
            tomlkit.dump(spec_dict, fh)

    def upload_spec(self, spec_file, pdf_file):
        speck = SpecificationService()
        if speck.is_there_a_spec():
            self.stderr.write(
                "There is already a spec present. Cannot proceed with upload."
            )
            return

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

        # plom wants numberToProduce to be set - so we set a dummy value here by hand
        # also make sure it is not set to zero
        # TODO - make a more elegant solution here.
        if "numberToProduce" not in spec_dict:
            spec_dict["numberToProduce"] = 1
        elif spec_dict["numberToProduce"] == 0:
            spec_dict["numberToProduce"] = 1

        # CAREFUL - vlad will change the underly dict, so pass it a copy
        vlad = SpecVerifier(copy.deepcopy(spec_dict))

        try:
            vlad.verifySpec()
            validated_spec = vlad.spec
        except ValueError as err:
            self.stderr.write(f"There was an error validating the spec: {err}")
            return

        self.stdout.write("Test specification validated.")

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

        # Load in the validated spec from vlad - not the original toml. This will be correctly populated
        # with any optional keys etc. See issue #88
        staging_spec = StagingSpecificationService()

        reference = ReferencePDFService()
        reference.new_pdf(
            staging_spec, "spec_reference.pdf", pdf_doc.page_count, pdf_doc_file
        )

        staging_spec.create_from_dict(validated_spec)

        speck.store_validated_spec(staging_spec.get_valid_spec_dict(verbose=False))
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
        speck = SpecificationService()
        self.stdout.write("Removing the test specification.")
        staging_spec.reset_specification()
        if speck.is_there_a_spec():
            speck.remove_spec()

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting of a classlist.",
        )
        sp_S = sub.add_parser("status", help="Show details of current test spec")
        sp_U = sub.add_parser("upload", help="Upload a test spec")
        sp_D = sub.add_parser(
            "download", help="Download the current test spec (if is valid)"
        )
        sp_R = sub.add_parser("remove", help="Remove the current test spec the server")

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
            self.download_spec()
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_test_spec")
